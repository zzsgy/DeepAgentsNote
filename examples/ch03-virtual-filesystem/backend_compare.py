from datetime import datetime
from pathlib import Path
from uuid import uuid4
from langchain_core.runnables import RunnableConfig
from typing import Any, Mapping

from deepagents import create_deep_agent
from deepagents.backends import (
    StateBackend,
    FilesystemBackend,
    StoreBackend,
    CompositeBackend,
)

# LangGraph:保存线程状态，以及提供跨线程Store
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

# LangChain: 识别实际的工具返回消息
from langchain_core.messages import ToolMessage

# 我们自己定义文件，只提供真实模型对象
from model_config import build_model

# 可选：state、filesystem、store、composite
EXPERIMENT = "state"

PROJECT_DIR = Path(__file__).resolve().parent

# 每次运行使用不同编号，避免覆盖以前的实验文件。
RUN_ID = (
    datetime.now().strftime("%Y%m%d-%H%M%S")
    + "_"
    + uuid4().hex[:8]
)

SYSTEM_PROMPT = """

你正在参加文件系统教学实验。

要求：
1. 文件相关任务必须调用内置文件工具，不得编造执行结果。
2. 用户要求读取时，必须调用 read_file，
   不能仅根据对话历史回答文件内容。
3. 文件不存在时，如实报告，不要主动创建它。
4. 写入任务完成后，按要求调用工具验证。
5. 不使用 task 委派任务，不调用 execute，不删除文件。
6. 用中文简洁说明结果。

"""
def show_result(title: str, result: Mapping[str, Any], start_index: int = 0) -> None:
    """
    只负责打印消息，不封装 agent.invoke()。
    start_index 用于跳过同线程保存的旧消息。
    """
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    new_messages = result["messages"][start_index:]
    tool_count = 0

    for message in new_messages:
        # 模型提出了哪些工具调用？
        tool_calls = getattr(message, "tool_calls", None)

        if tool_calls:
            for call in tool_calls:
                print("\n[模型请求调用工具]")
                print("名称：", call["name"])
                print("参数：", call["args"])

        # 工具实际上返回了什么？
        if isinstance(message, ToolMessage):
            tool_count += 1
            print("\n[工具实际返回]")
            print("名称：", message.name)
            print("状态：", message.status)
            print("内容：", message.content)

    print("\n[Agent 最终回答]")
    print(result["messages"][-1].content)

    if tool_count == 0:
        print(
            "\n警告：本轮没有观察到工具返回，"
            "不能仅凭 Agent 的文字声称实验成功。"
        )

def main():
    model = build_model()
    print("当前实验：", EXPERIMENT)
    print("本次编号：", RUN_ID)

    # --------------------------------------------------
    # 第一组：StateBackend
    # --------------------------------------------------
    if EXPERIMENT == "state":
        checkpointer = InMemorySaver()

        agent = create_deep_agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            backend=StateBackend(),
            checkpointer=checkpointer,
        )

        file_path = "/notes/demo.md"
        disk_root = None
        store = None

    # --------------------------------------------------
    # 第二组：FilesystemBackend
    # --------------------------------------------------
    elif EXPERIMENT == "filesystem":
        # 只允许操作本次新建的实验目录。
        disk_root = (
                PROJECT_DIR
                / "manual_runs"
                / RUN_ID
                / "filesystem"
        )
        disk_root.mkdir(parents=True, exist_ok=False)

        checkpointer = InMemorySaver()

        agent = create_deep_agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            backend=FilesystemBackend(
                root_dir=str(disk_root),
                virtual_mode=True,
            ),
            checkpointer=checkpointer,
        )

        file_path = "/notes/demo.md"
        store = None

        print("实际磁盘根目录：", disk_root)

    # --------------------------------------------------
    # 第三组：StoreBackend
    # --------------------------------------------------
    elif EXPERIMENT == "store":
        checkpointer = InMemorySaver()

        # 这是 LangGraph 的内存 Store。
        store = InMemoryStore()

        agent = create_deep_agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            backend=StoreBackend(
                # 本地教学使用固定用户空间。
                # 不依赖服务器提供的 server_info。
                namespace=lambda runtime: ("student-001",),
            ),
            checkpointer=checkpointer,
            store=store,
        )

        file_path = "/notes/demo.md"
        disk_root = None

    # --------------------------------------------------
    # 第四组：CompositeBackend
    # --------------------------------------------------
    elif EXPERIMENT == "composite":
        checkpointer = InMemorySaver()
        store = InMemoryStore()

        agent = create_deep_agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            backend=CompositeBackend(
                # 普通路径：当前线程的 State。
                default=StateBackend(),

                # /memories/ 路径：跨线程的 Store。
                routes={
                    "/memories/": StoreBackend(
                        namespace=lambda runtime: (
                            "student-001",
                        ),
                    ),
                },
            ),
            checkpointer=checkpointer,
            store=store,
        )

        file_path = "/memories/demo.md"
        disk_root = None

    else:
        raise ValueError(
            "EXPERIMENT 必须是 state、filesystem、"
            "store 或 composite"
        )

    # --------------------------------------------------
    # 两个独立的 LangGraph 对话线程。
    # --------------------------------------------------
    config_a: RunnableConfig = {
        "configurable": {
            "thread_id": f"{RUN_ID}-A",
        },
        "recursion_limit": 30,
    }

    config_b: RunnableConfig = {
        "configurable": {
            "thread_id": f"{RUN_ID}-B",
        },
        "recursion_limit": 30,
    }

    # --------------------------------------------------
    # 第一步：A 线程写入，并使用文件工具验证。
    # --------------------------------------------------
    write_prompt = f"""
请完成以下文件实验，必须真实调用工具：

1. 用 write_file 向 {file_path} 写入以下三行内容：
课程：Deep Agents 第三章
TODO：完成 Backend 对比实验
偏好：使用中文解释

2. 用 read_file 读取刚才的文件。
3. 用 glob 在 / 下查找 Markdown 文件。
4. 用 grep 在 / 下搜索字面量 TODO，
   output_mode 使用 content。

不要创建其他文件，不要删除文件。
最后简要说明实际执行结果。
"""

    result_a1 = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": write_prompt,
                }
            ]
        },
        config=config_a,
    )
    show_result("第一步：线程 A 写入并验证", result_a1)
    # 记录旧消息数，下一次打印时只展示新增消息。
    old_message_count = len(result_a1["messages"])

    # --------------------------------------------------
    # 第二步：仍然使用 A 线程，再次读取。
    # --------------------------------------------------

    result_a2 = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"请现在调用 read_file 读取 {file_path}。"
                        "不要从对话记忆直接复述，"
                        "不要写入或创建任何文件。"
                    ),
                }
            ]
        },
        config=config_a,
    )

    show_result(
        "第二步：同一线程 A 再次读取",
        result_a2,
        start_index=old_message_count,
    )
    # --------------------------------------------------
    # 第三步：换成 B 线程，读取相同路径。
    # --------------------------------------------------
    result_b = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"请调用 read_file 读取 {file_path}。"
                        "如果文件不存在，请如实说明，"
                        "禁止写入或创建文件。"
                    ),
                }
            ]
        },
        config=config_b,
    )

    show_result("第三步：新线程 B读取", result_b)

    # --------------------------------------------------
    # 第四步：直接检查真实存储，不能只听模型自述。
    # --------------------------------------------------
    print("\n" + "=" * 60)
    print("第四步：检查实际存储")
    print("=" * 60)

    snapshot_a = agent.get_state(config_a)
    snapshot_b = agent.get_state(config_b)

    print(
        "线程 A 的 State.files 路径：",
        list(snapshot_a.values.get("files", {}).keys()),
    )

    print(
        "线程 B 的 State.files 路径：",
        list(snapshot_b.values.get("files", {}).keys()),
    )

    if EXPERIMENT == "state":
        files_a = snapshot_a.values.get("files", {})
        file_data = files_a.get(file_path)

        if file_data:
            print("State 中的实际内容：")
            print(file_data["content"])
        else:
            print("没有找到目标文件：检查模型是否真正写入。")

    elif EXPERIMENT == "filesystem":
        real_file = disk_root / "notes" / "demo.md"

        print("真实磁盘文件：", real_file)
        print("文件是否存在：", real_file.exists())

        if real_file.exists():
            print("磁盘实际内容：")
            print(real_file.read_text(encoding="utf-8"))

    elif EXPERIMENT in {"store", "composite"}:
        # 直接观察 LangGraph Store 中保存的数据。
        items = store.search(("student-001",))

        print("Store 中的记录数：", len(items))

        for item in items:
            print("namespace：", item.namespace)
            print("key：", item.key)
            print("value：", item.value)

        # --------------------------------------------------
        # 第五步：Composite 额外验证默认临时路径。
        # --------------------------------------------------
    if EXPERIMENT == "composite":
        previous_count = len(result_a2["messages"])

        temp_a = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "请调用 write_file，在 /scratch/plan.md "
                            "写入：这是仅属于线程 A 的临时计划。"
                            "然后用 read_file 读回验证。"
                        ),
                    }
                ]
            },
            config=config_a,
        )

        show_result(
            "第五步：A 写入默认 State 路由",
            temp_a,
            start_index=previous_count,
        )

        previous_count_b = len(result_b["messages"])

        temp_b = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "请调用 read_file 读取 /scratch/plan.md。"
                            "如果不存在，如实报告，禁止创建它。"
                        ),
                    }
                ]
            },
            config=config_b,
        )

        show_result(
            "第六步：B 尝试读取临时文件",
            temp_b,
            start_index=previous_count_b,
        )

        state_a = agent.get_state(config_a)
        print(
            "\nA 的最终 State.files：",
            list(state_a.values.get("files", {}).keys()),
        )

if __name__ == "__main__":
    main()
