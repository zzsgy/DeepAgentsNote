"""确定性工具调用驱动器：不调用任何大模型服务，不伪造工具执行结果。"""

import json
from uuid import uuid4

from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver


class ScriptedToolModel(BaseChatModel):
    """将实验指定的 JSON 转成标准 ToolCall；不是具有推理能力的大模型。"""

    @property
    def _llm_type(self):
        return "offline-scripted-tool-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if isinstance(messages[-1], ToolMessage):
            response = AIMessage(content="本次工具执行结束。")
        elif isinstance(messages[-1], HumanMessage):
            request = json.loads(messages[-1].content)
            response = AIMessage(content="", tool_calls=[{
                "name": request["tool"], "args": request["args"],
                "id": uuid4().hex, "type": "tool_call",
            }])
        else:
            raise RuntimeError("测试驱动只接受一次 JSON 请求或工具返回结果")
        return ChatResult(generations=[ChatGeneration(message=response)])

    def get_num_tokens_from_messages(self, messages, tools=None):
        # 仅给框架一个离线估计，避免测试模型下载 tokenizer；不用于验证压缩阈值。
        return sum(len(str(message.content)) // 3 + 8 for message in messages)


class Driver:
    def __init__(self, backend, *, store=None, permissions=None, checkpointer=None):
        self.checkpointer = checkpointer if checkpointer is not None else InMemorySaver()
        self.agent = create_deep_agent(
            model=ScriptedToolModel(), backend=backend, store=store,
            permissions=permissions, checkpointer=self.checkpointer,
        )
        self.calls = []

    def call(self, tool, *, thread="A", **args):
        if tool not in {"ls", "glob", "grep", "read_file", "write_file", "edit_file", "delete"}:
            raise ValueError("本实验只驱动七种文件工具，不驱动 task 或 execute")
        result = self.agent.invoke(
            {"messages": [HumanMessage(content=json.dumps(
                {"tool": tool, "args": args}, ensure_ascii=False,
            ))]},
            config={"configurable": {"thread_id": thread}, "recursion_limit": 12},
        )
        message = next(m for m in reversed(result["messages"]) if isinstance(m, ToolMessage))
        self.calls.append({"thread": thread, "tool": tool, "args": args,
                           "status": message.status, "content": message.content})
        return message

    def files(self, thread="A"):
        snapshot = self.agent.get_state({"configurable": {"thread_id": thread}})
        return snapshot.values.get("files", {})
