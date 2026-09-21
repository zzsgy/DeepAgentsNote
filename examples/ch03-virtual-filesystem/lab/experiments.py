"""每个 experiment_* 是一组可单独阅读、运行、修改的对比实验。"""

import json
import subprocess
import sys
import traceback

from deepagents import FilesystemPermission
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

from lab.driver import Driver
from lab.report import PROJECT, Report
from lab.policy import PolicyWrapper


def make_driver(report, label, backend, **kwargs):
    driver = Driver(backend, **kwargs)
    report.drivers.append((label, driver))
    return driver


def text(message):
    return str(message.content)


def disk(report, name):
    root = report.root / name
    root.mkdir()
    return FilesystemBackend(root_dir=str(root), virtual_mode=True), root


def experiment_tools(report):
    """相同内容、相同工具调用：只更换 Backend（控制变量）。"""
    local, root = disk(report, "tool-filesystem")
    store = InMemoryStore()
    backends = [
        ("State", StateBackend(), None),
        ("Filesystem", local, None),
        ("Store", StoreBackend(namespace=lambda _: ("tool-user",)), store),
    ]
    content = "第1行：学习 Backend\n第2行：TODO 阅读\n第3行：TODO 实验\n第4行：完成\n"
    for label, backend, shared_store in backends:
        driver = make_driver(report, label, backend, store=shared_store)
        result = driver.call("write_file", file_path="/notes/demo.md", content=content)
        report.check(f"{label}: write_file", result.status == "success", text(result))
        result = driver.call("read_file", file_path="/notes/demo.md")
        report.check(f"{label}: read_file 读回原文", result.status == "success" and all(line in text(result) for line in content.splitlines()), text(result))
        result = driver.call("read_file", file_path="/notes/demo.md", offset=1, limit=2)
        report.check(f"{label}: offset=1 从第2行读两行",
                     "第2行" in text(result) and "第3行" in text(result)
                     and "第1行：" not in text(result) and "第4行：" not in text(result), text(result))
        result = driver.call("ls", path="/notes/")
        report.check(f"{label}: ls", "/notes/demo.md" in text(result), text(result))
        result = driver.call("glob", pattern="**/*.md", path="/")
        report.check(f"{label}: glob", "/notes/demo.md" in text(result), text(result))
        for mode in ("files_with_matches", "content", "count"):
            result = driver.call("grep", pattern="TODO", path="/", output_mode=mode)
            expected = "第2行" if mode == "content" else "2" if mode == "count" else "/notes/demo.md"
            report.check(f"{label}: grep/{mode}", result.status == "success" and expected in text(result), text(result))
        result = driver.call("edit_file", file_path="/notes/demo.md", old_string="TODO 阅读", new_string="DONE 阅读")
        report.check(f"{label}: edit_file", result.status == "success", text(result))
        result = driver.call("read_file", file_path="/notes/demo.md")
        report.check(f"{label}: 编辑确实改变内容", "DONE 阅读" in text(result) and "TODO 阅读" not in text(result), text(result))
        before = text(result)
        error = driver.call("edit_file", file_path="/notes/demo.md", old_string="NOT_PRESENT", new_string="不能插入")
        after = driver.call("read_file", file_path="/notes/demo.md")
        report.check(f"{label}: 不存在的替换目标被拒绝且原文不变",
                     error.status == "error" and text(after) == before, text(error))
        driver.call("write_file", file_path="/notes/demo.md", content="完整覆盖后的新内容")
        result = driver.call("read_file", file_path="/notes/demo.md")
        report.check(f"{label}: v0.7 write_file 是覆盖而非追加",
                     "完整覆盖后的新内容" in text(result) and "TODO" not in text(result), text(result))
        driver.call("write_file", file_path="/notes/disposable.txt", content="只删除本次新建的实验文件")
        result = driver.call("delete", file_path="/notes/disposable.txt")
        missing = driver.call("read_file", file_path="/notes/disposable.txt")
        report.check(f"{label}: delete 后读不到测试文件", result.status == "success" and missing.status == "error", text(missing))
        if label == "State":
            report.check("State: 文件确实存在 Agent State.files", "/notes/demo.md" in driver.files(), driver.files())
        elif label == "Filesystem":
            report.check("Filesystem: 实际文件落在指定磁盘目录", (root / "notes/demo.md").read_text(encoding="utf-8") == "完整覆盖后的新内容", str(root / "notes/demo.md"))
        else:
            items = store.search(("tool-user",))
            report.check("Store: 文件确实写入 Store namespace", bool(items), [item.key for item in items])


def experiment_lifecycle(report):
    """同一线程、新线程、共享状态保存器、共享存储，是不同维度。"""
    state = make_driver(report, "state-A", StateBackend())
    state.call("write_file", file_path="/memo.txt", content="STATE_MARKER")
    result = state.call("read_file", file_path="/memo.txt", thread="A")
    report.check("State: 同线程下一轮可读", "STATE_MARKER" in text(result), text(result))
    result = state.call("read_file", file_path="/memo.txt", thread="B")
    report.check("State: 新线程看不到 A 的文件", result.status == "error", text(result))
    restored = make_driver(report, "state-restored", StateBackend(), checkpointer=state.checkpointer)
    result = restored.call("read_file", file_path="/memo.txt", thread="A")
    report.check("State: 新 Agent + 同一 Checkpointer + 原 thread 可恢复", "STATE_MARKER" in text(result), text(result))
    fresh = make_driver(report, "state-fresh-checkpointer", StateBackend())
    result = fresh.call("read_file", file_path="/memo.txt", thread="A")
    report.check("State: 相同 thread_id + 新内存 Checkpointer 不能恢复", result.status == "error", text(result))

    backend, root = disk(report, "lifecycle-filesystem")
    fs = make_driver(report, "filesystem-A", backend)
    fs.call("write_file", file_path="/memo.txt", content="DISK_MARKER")
    result = fs.call("read_file", file_path="/memo.txt", thread="B")
    report.check("Filesystem: 共享 root_dir 的新线程可读", "DISK_MARKER" in text(result), text(result))
    fs2 = make_driver(report, "filesystem-new-agent", FilesystemBackend(root_dir=str(root), virtual_mode=True))
    result = fs2.call("read_file", file_path="/memo.txt")
    report.check("Filesystem: 新 Agent 指向原磁盘目录仍可读", "DISK_MARKER" in text(result), text(result))

    store = InMemoryStore()
    alice = make_driver(report, "store-alice", StoreBackend(namespace=lambda _: ("alice",)), store=store)
    alice.call("write_file", file_path="/memo.txt", content="STORE_MARKER")
    result = alice.call("read_file", file_path="/memo.txt", thread="B")
    report.check("Store: 同一 Store/namespace 可跨线程", "STORE_MARKER" in text(result), text(result))
    bob = make_driver(report, "store-bob", StoreBackend(namespace=lambda _: ("bob",)), store=store)
    result = bob.call("read_file", file_path="/memo.txt")
    report.check("Store: 不同 namespace 隔离", result.status == "error", text(result))
    alice2 = make_driver(report, "store-alice-new-agent", StoreBackend(namespace=lambda _: ("alice",)), store=store)
    result = alice2.call("read_file", file_path="/memo.txt")
    report.check("Store: 新 Agent 复用相同 Store/namespace 可读", "STORE_MARKER" in text(result), text(result))
    empty = make_driver(report, "store-new-instance", StoreBackend(namespace=lambda _: ("alice",)), store=InMemoryStore())
    result = empty.call("read_file", file_path="/memo.txt")
    report.check("Store: 新 InMemoryStore 不含旧数据", result.status == "error", text(result))

    # 新 Python 进程，而不只是重新构造 Python 对象；shell=False。
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(PROJECT / "restart_probe.py"), str(root)],
        capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )
    report.check("独立进程探针正常完成", completed.returncode == 0, completed.stderr or completed.stdout)
    if completed.returncode == 0:
        observed = json.loads(completed.stdout)
        report.check("真正的新进程: 磁盘保留、内存 State/Store 不保留",
                     observed["disk_found"] and not observed["state_found"] and not observed["store_found"], observed)


def experiment_composite(report):
    store = InMemoryStore()
    local, root = disk(report, "composite-project")
    backend = CompositeBackend(default=StateBackend(), routes={
        "/memories/": StoreBackend(namespace=lambda _: ("alice",)),
        "/project/": local,
    })
    driver = make_driver(report, "composite", backend, store=store)
    paths = {"/scratch/plan.md": "TEMP_MARKER", "/memories/preferences.md": "MEMORY_MARKER",
             "/project/report.md": "PROJECT_MARKER"}
    for path, content in paths.items():
        driver.call("write_file", file_path=path, content=content)
    report.check("Composite: 只有默认路由文件进入 State.files",
                 set(driver.files()) == {"/scratch/plan.md"}, driver.files())
    report.check("Composite: /project/ 前缀剥离后映射磁盘",
                 (root / "report.md").read_text(encoding="utf-8") == "PROJECT_MARKER"
                 and not (root / "project/report.md").exists(), str(root))
    report.check("Composite: /memories/ 进入 Store",
                 bool(store.search(("alice",))), [i.key for i in store.search(("alice",))])
    for path, marker in paths.items():
        result = driver.call("read_file", file_path=path, thread="B")
        expected = path != "/scratch/plan.md"
        report.check(f"Composite: 新线程读取 {path}，预期{'可见' if expected else '不可见'}",
                     (marker in text(result)) if expected else result.status == "error", text(result))
    result = driver.call("glob", pattern="**/*.md", path="/", thread="A")
    report.check("Composite: glob 聚合并保留外部路径", all(p in text(result) for p in paths), text(result))
    result = driver.call("grep", pattern="MARKER", path="/", output_mode="files_with_matches")
    report.check("Composite: grep 跨路由聚合", all(p in text(result) for p in paths), text(result))
    driver.call("write_file", file_path="/memory/typo.md", content="TYPO_MARKER")
    result = driver.call("read_file", file_path="/memory/typo.md", thread="B")
    report.check("Composite: 拼错 /memories/ 会进入 default，不自动成为长期记忆", result.status == "error", text(result))


def experiment_permissions(report):
    local, root = disk(report, "permission-fixtures")
    # 全部为人工构造的假资料，不读取真实凭证。
    local.write("/policies/rule.md", "ORIGINAL_POLICY")
    local.write("/secrets/fake.txt", "FAKE_SECRET_MARKER")
    rules = [
        FilesystemPermission(operations=["read", "write"], paths=["/secrets/**"], mode="deny"),
        FilesystemPermission(operations=["write"], paths=["/policies/**"], mode="deny"),
    ]
    driver = make_driver(report, "permissions", local, permissions=rules)
    result = driver.call("read_file", file_path="/policies/rule.md")
    report.check("Permission: 可读制度", "ORIGINAL_POLICY" in text(result), text(result))
    for tool, args in [
        ("write_file", {"content": "MODIFIED"}),
        ("edit_file", {"old_string": "ORIGINAL_POLICY", "new_string": "MODIFIED"}),
        ("delete", {}),
    ]:
        result = driver.call(tool, file_path="/policies/rule.md", **args)
        report.check(f"Permission: 拒绝 {tool} 且磁盘原文不变",
                     result.status == "error" and (root / "policies/rule.md").read_text(encoding="utf-8") == "ORIGINAL_POLICY", text(result))
    result = driver.call("read_file", file_path="/secrets/fake.txt")
    report.check("Permission: 拒绝读取假秘密", result.status == "error" and "FAKE_SECRET_MARKER" not in text(result), text(result))
    result = driver.call("grep", pattern="FAKE_SECRET_MARKER", path="/", output_mode="content")
    report.check("Permission: 全局 grep 正常执行但不泄露被拒绝文件内容", result.status == "success" and "FAKE_SECRET_MARKER" not in text(result), text(result))
    result = driver.call("write_file", file_path="/other/open.txt", content="UNMATCHED_ALLOWED")
    report.check("Permission: 没命中规则默认允许", result.status == "success" and (root / "other/open.txt").exists(), text(result))
    allow = FilesystemPermission(operations=["write"], paths=["/workspace/**"], mode="allow")
    deny = FilesystemPermission(operations=["write"], paths=["/workspace/private/**"], mode="deny")
    wrong = make_driver(report, "wrong-order", local, permissions=[allow, deny])
    result = wrong.call("write_file", file_path="/workspace/private/demo.txt", content="FIRST_MATCH")
    report.check("反例: 宽泛 allow 放前面会覆盖后面的 deny", result.status == "success", text(result))
    right = make_driver(report, "right-order", local, permissions=[deny, allow])
    result = right.call("write_file", file_path="/workspace/private/demo.txt", content="SHOULD_NOT_CHANGE")
    report.check("纠正: 具体 deny 放前面", result.status == "error" and (root / "workspace/private/demo.txt").read_text(encoding="utf-8") == "FIRST_MATCH", text(result))
    closed = make_driver(report, "allowlist", local, permissions=[allow,
        FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="deny")])
    result = closed.call("write_file", file_path="/outside-blocked.txt", content="BLOCKED")
    report.check("Permission: 白名单末尾 deny 阻止其他路径", result.status == "error" and not (root / "outside-blocked.txt").exists(), text(result))

    # 越界目标仍在本次实验目录内，不试探真实个人文件。
    outside = report.root / "outside-fixture.txt"
    outside.write_text("OUTSIDE_TEST_MARKER", encoding="utf-8")
    try:
        result = local.read("/../outside-fixture.txt")
        denied = result.error is not None
        observed = result.error
    except (ValueError, PermissionError) as exc:
        denied, observed = True, str(exc)
    report.check("Filesystem virtual_mode: 拒绝 .. 路径越界", denied, observed)


def experiment_policy(report):
    local, root = disk(report, "policy-wrapper")
    local.write("/policies/rule.md", "POLICY_ORIGINAL")
    wrapper = PolicyWrapper(local, max_bytes=80)
    driver = make_driver(report, "policy-wrapper", wrapper)
    driver.call("write_file", file_path="/notes/draft.txt", content="short")
    result = driver.call("edit_file", file_path="/notes/draft.txt", old_string="short", new_string="brief")
    report.check("PolicyWrapper: 合规写入与编辑真正落盘",
                 result.status == "success" and (root / "notes/draft.txt").read_text(encoding="utf-8") == "brief", text(result))
    for tool, args in [
        ("write_file", {"content": "X" * 81}),
        ("edit_file", {"old_string": "brief", "new_string": "X" * 81}),
    ]:
        result = driver.call(tool, file_path="/notes/draft.txt", **args)
        report.check(f"PolicyWrapper: {tool} 超限被拒绝且原文不变",
                     result.status == "error" and (root / "notes/draft.txt").read_text(encoding="utf-8") == "brief", text(result))
    for tool, args in [
        ("write_file", {"content": "changed"}),
        ("edit_file", {"old_string": "POLICY_ORIGINAL", "new_string": "changed"}),
        ("delete", {}),
    ]:
        result = driver.call(tool, file_path="/policies/rule.md", **args)
        report.check(f"PolicyWrapper: 保护文件免于 {tool}", result.status == "error"
                     and (root / "policies/rule.md").read_text(encoding="utf-8") == "POLICY_ORIGINAL", text(result))
    result = wrapper.delete("/policies")
    report.check("PolicyWrapper: 拒绝目录本身（不依赖末尾斜杠）",
                 result.error is not None and (root / "policies/rule.md").exists(), result.error)
    # 纯策略判定，不对根目录发起实际删除调用。
    report.check("PolicyWrapper: 父目录删除策略判定为拒绝", wrapper._reason("/", deleting=True) is not None, "只调用判断函数，没有删除根目录")
    result = driver.call("read_file", file_path="/policies/rule.md")
    report.check("PolicyWrapper: 示例保护变更但不禁止读", "POLICY_ORIGINAL" in text(result), text(result))
    # 路由内部看到的是去掉 /project/ 后的路径。
    routed = make_driver(report, "policy-inside-composite", CompositeBackend(
        default=StateBackend(), routes={"/project/": wrapper},
    ))
    result = routed.call("write_file", file_path="/project/policies/rule.md", content="changed")
    report.check("PolicyWrapper: Composite 路由内用 /policies 规则即可命中",
                 result.status == "error" and wrapper.audit[-1]["path"] == "/policies/rule.md", wrapper.audit[-1])
    report.check("PolicyWrapper: 留下成功/拒绝审计且不含正文",
                 any(r["allowed"] for r in wrapper.audit) and any(not r["allowed"] for r in wrapper.audit)
                 and all("content" not in r for r in wrapper.audit), wrapper.audit)


EXPERIMENTS = {
    "tools": experiment_tools,
    "lifecycle": experiment_lifecycle,
    "composite": experiment_composite,
    "permissions": experiment_permissions,
    "policy": experiment_policy,
}


def run_suite(only=None, verbose=True):
    report = Report(verbose=verbose)
    selected = EXPERIMENTS if only is None else {only: EXPERIMENTS[only]}
    for name, experiment in selected.items():
        report.group = name
        if verbose:
            print(f"\n=== {name} ===", flush=True)
        try:
            experiment(report)
        except Exception:
            report.check("实验发生未预期异常", False, traceback.format_exc())
    result = report.save()
    return report, result
