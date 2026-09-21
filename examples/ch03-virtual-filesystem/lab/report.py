"""记录真实观察结果；失败不会被转换为成功。"""

import json
import platform
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4


PROJECT = Path(__file__).resolve().parents[1]


class Report:
    def __init__(self, verbose=True):
        runs = PROJECT / "runs"
        # 不沿用户后来创建的符号链接把实验写到其他目录。
        if runs.is_symlink() or (runs.exists() and runs.resolve().parent != PROJECT):
            raise RuntimeError("runs 必须是本项目内的普通目录")
        runs.mkdir(exist_ok=True)
        self.root = runs / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8])
        self.root.mkdir()
        self.checks = []
        self.drivers = []
        self.verbose = verbose
        self.group = ""

    def check(self, name, condition, observed=""):
        row = {"group": self.group, "name": name, "passed": bool(condition),
               "observed": str(observed)}
        self.checks.append(row)
        if self.verbose:
            print(f"  [{'PASS' if condition else 'FAIL'}] {name}", flush=True)
            if not condition:
                print(f"         实际结果：{observed}", flush=True)

    def save(self):
        passed = sum(row["passed"] for row in self.checks)
        result = {
            "python": platform.python_version(),
            "packages": {p: version(p) for p in ("deepagents", "langchain", "langchain-core", "langgraph")},
            "passed": passed, "total": len(self.checks), "checks": self.checks,
            "tool_traces": [{"label": label, "calls": driver.calls}
                            for label, driver in self.drivers],
        }
        (self.root / "results.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        lines = ["# 第三章实验实际运行记录", "",
                 f"结果：{passed}/{len(self.checks)} 检查通过。", "",
                 "这是代码行为验证，不是学习者掌握度评分。", "",
                 f"Python: {result['python']}；依赖: {result['packages']}", ""]
        previous = None
        for row in self.checks:
            if row["group"] != previous:
                lines += [f"## {row['group']}", ""]
                previous = row["group"]
            lines += [f"- {'PASS' if row['passed'] else 'FAIL'}：{row['name']}", "",
                      "```text", row["observed"], "```", ""]
        lines += ["## 如何解读", "",
                  "只有 PASS 的观察才能用作本次行为证据；有 FAIL 时先看上方实际输出。",
                  "完整工具参数、状态和原始返回值见同目录 results.json。",
                  "预期对比与适用前提见项目 README；请在学习记录模板中写自己的结论。"]
        (self.root / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
        return result
