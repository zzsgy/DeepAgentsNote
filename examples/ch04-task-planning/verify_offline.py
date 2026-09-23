"""离线行为检查；固定脚本模型不具备自主规划能力，不会访问模型或搜索服务。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

# 导入框架前关闭追踪、阻断网络；没有凭证也可以运行。
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"


def deny_network(event, args):
    if event in ("socket.connect", "socket.getaddrinfo"):
        raise RuntimeError("离线验证禁止网络连接")


sys.addaudithook(deny_network)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware import SummarizationMiddleware
from langchain.agents.middleware import TodoListMiddleware
from pydantic import Field, PrivateAttr

from course import build_agent, collect_evidence, export_result, file_text, read_config


class ScriptedModel(BaseChatModel):
    actions: list[dict] = Field(default_factory=list)
    _cursor: int = PrivateAttr(default=0)
    _seen: list = PrivateAttr(default_factory=list)

    @property
    def _llm_type(self):
        return "offline-scripted-not-real-llm"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._seen.append(list(messages))
        if self._cursor < len(self.actions):
            call = self.actions[self._cursor]
            self._cursor += 1
            message = AIMessage(content="", tool_calls=[{
                **call, "id": uuid4().hex, "type": "tool_call"}])
        else:
            message = AIMessage(content="离线脚本结束；不是自主研究结果。")
        return ChatResult(generations=[ChatGeneration(message=message)])


def action(name, **args):
    return {"name": name, "args": args}


def plan(*statuses):
    return [{"content": content, "status": status} for content, status in zip(
        ("收集资料", "写报告", "读取并检查报告"), statuses)]


def internet_search(query: str, max_results: int = 5) -> dict:
    """只返回固定测试文本，不访问 Tavily，也不模拟真实产品结论。"""
    return {"source": "offline_fixture", "results": [{"content": "固定测试资料"}]}


def thread(name):
    return {"configurable": {"thread_id": name}}


class Chapter4Tests(unittest.TestCase):
    def test_workflow_and_export(self):
        report = "# 离线测试报告\n\n固定文本，仅验证工具连接，不是实时研究。"
        model = ScriptedModel(actions=[
            action("write_todos", todos=plan("in_progress", "pending", "pending")),
            action("internet_search", query="测试"),
            action("write_file", file_path="/notes.md", content="固定测试资料"),
            action("write_todos", todos=plan("completed", "in_progress", "pending")),
            action("write_file", file_path="/final_report.md", content=report),
            action("read_file", file_path="/final_report.md"),
            action("write_todos", todos=plan("completed", "completed", "completed")),
        ])
        agent = build_agent(model, internet_search)
        result = agent.invoke({"messages": [HumanMessage("运行离线脚本")]})
        evidence = collect_evidence(result)
        self.assertEqual(len(evidence["todo_updates"]), 3)
        self.assertEqual(len(evidence["tool_calls"]), 7)
        self.assertTrue(all(c["has_response"] for c in evidence["tool_calls"]))
        self.assertEqual(result["todos"], plan("completed", "completed", "completed"))
        self.assertEqual(file_text(result, "/final_report.md"), report)
        responses = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        self.assertIn("离线测试报告", str(responses[-2].content))
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "run"
            export_result(result, target)
            self.assertEqual((target / "final_report.md").read_text(encoding="utf-8"), report)
            self.assertTrue((target / "evidence.json").is_file())

    def test_todos_replace_entire_list(self):
        replacement = [{"content": "只保留新任务", "status": "pending"}]
        agent = build_agent(ScriptedModel(actions=[
            action("write_todos", todos=plan("pending", "pending", "pending")),
            action("write_todos", todos=replacement),
        ]), internet_search)
        result = agent.invoke({"messages": [HumanMessage("测试整体替换")]})
        self.assertEqual(result["todos"], replacement)

    def test_checkpoint_and_thread_isolation(self):
        agent = build_agent(ScriptedModel(actions=[
            action("write_todos", todos=plan("in_progress", "pending", "pending")),
            action("write_file", file_path="/notes.md", content="THREAD_A_ONLY"),
        ]), internet_search, checkpointer=InMemorySaver())
        for text in ("创建", "继续"):
            agent.invoke({"messages": [HumanMessage(text)]}, config=thread("A"))
        state_a = agent.get_state(thread("A")).values
        self.assertEqual(len(state_a["todos"]), 3)
        self.assertEqual(file_text(state_a, "/notes.md"), "THREAD_A_ONLY")
        agent.invoke({"messages": [HumanMessage("新线程")]}, config=thread("B"))
        state_b = agent.get_state(thread("B")).values
        self.assertFalse(state_b.get("todos"))
        self.assertFalse(state_b.get("files"))

    def test_missing_file_is_not_completion(self):
        agent = build_agent(ScriptedModel(actions=[
            action("write_todos", todos=plan("in_progress", "pending", "pending")),
            action("read_file", file_path="/missing.md"),
        ]), internet_search)
        result = agent.invoke({"messages": [HumanMessage("测试不存在的文件")]})
        responses = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        self.assertIn("not found", str(responses[-1].content).lower())
        self.assertFalse(collect_evidence(result)["report_present"])
        self.assertTrue(any(t["status"] != "completed" for t in result["todos"]))

    def test_summary_preserves_todos_and_history(self):
        todos = plan("completed", "in_progress", "pending")
        model = ScriptedModel(actions=[action("write_todos", todos=todos)])
        backend = StateBackend()
        agent = create_deep_agent(
            model=model, backend=backend, checkpointer=InMemorySaver(),
            middleware=[TodoListMiddleware(), SummarizationMiddleware(
                model=FakeListChatModel(responses=["测试摘要：已收集资料，正在写报告。"]),
                backend=backend, trigger=("messages", 8), keep=("messages", 2))],
        )
        agent.invoke({"messages": [HumanMessage("建计划")]}, config=thread("summary"))
        history = []
        for index in range(5):
            history.extend([HumanMessage(f"历史 {index} KEEP_HISTORY_MARKER"), AIMessage("答复")])
        history.append(HumanMessage("继续"))
        agent.invoke({"messages": history}, config=thread("summary"))
        state = agent.get_state(thread("summary")).values
        self.assertEqual(state["todos"], todos)
        # 私有字段只用于这个固定版本的测试，不是稳定公共接口。
        path = state["_summarization_event"]["file_path"]
        self.assertIn("KEEP_HISTORY_MARKER", file_text(state, path))
        self.assertLess(len(model._seen[-1]), len(state["messages"]))
        model.actions.append(action("read_file", file_path=path, limit=100))
        agent.invoke({"messages": [HumanMessage("读回历史")]}, config=thread("summary"))
        state = agent.get_state(thread("summary")).values
        responses = [m for m in state["messages"] if isinstance(m, ToolMessage)]
        self.assertIn("KEEP_HISTORY_MARKER", str(responses[-1].content))

    def test_missing_config_fails_locally(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"MODEL_NAME": "NOT_A_FALLBACK"}):
                with self.assertRaisesRegex(ValueError, "MODEL_NAME"):
                    read_config(Path(temp))


if __name__ == "__main__":
    unittest.main(verbosity=2)
