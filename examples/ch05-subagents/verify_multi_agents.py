"""不读 .env、不连接网络的固定响应测试；不代表真实模型会自主协作。"""

import json
import os
import sys
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"


def block_network(event, args):
    if event in ("socket.connect", "socket.getaddrinfo"):
        raise AssertionError("离线验证禁止网络连接。")


sys.addaudithook(block_network)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field, PrivateAttr

import multi_agent_example as example


class ScriptedModel(BaseChatModel):
    """按固定规则生成工具调用；执行的是例子中的真实 Agent 图和 Python 工具。"""

    bound_names: list[str] = Field(default_factory=list)
    _seen: list = PrivateAttr(default_factory=list)

    @property
    def _llm_type(self):
        return "scripted-offline-multi-agent-not-a-real-llm"

    def bind_tools(self, tools, **kwargs):
        return self.model_copy(update={"bound_names": [tool.name for tool in tools]})

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        prompt = str(messages[0].content)
        role = next((name for phrase, name in (
            ("你是数据收集员", "data-collector"),
            ("你是数据分析员", "data-analyzer"),
            ("你是报告写作员", "report-writer"),
        ) if phrase in prompt), "supervisor")
        self._seen.append((role, list(messages), list(self.bound_names)))
        results = [m for m in messages if isinstance(m, ToolMessage)]
        task_input = next(m.content for m in messages if isinstance(m, HumanMessage))

        def call(name, args, identifier):
            return AIMessage(content=f"{role}: INTERNAL_STEP", tool_calls=[{
                "name": name, "args": args, "id": identifier,
            }])

        def todos(statuses):
            return [{"content": text, "status": status} for text, status in zip(
                ("收集数据", "分析数据", "编写报告"), statuses, strict=True
            )]

        def received(identifier):
            return next(m.content for m in results if m.tool_call_id == identifier)

        if role == "data-collector":
            answer = (call("read_sales_data", {}, "read") if not results
                      else AIMessage(content=results[-1].content))
        elif role == "data-analyzer":
            payload = json.loads(task_input)
            if not results:
                answer = call("statistical_analysis", {
                    "months": payload["months"], "sales": payload["sales"],
                }, "calculate")
            else:
                answer = AIMessage(content=json.dumps({
                    "statistics": json.loads(results[-1].content),
                    "unit": payload["unit"], "source": payload["source"],
                    "limitations": payload["limitations"],
                }, ensure_ascii=False))
        elif role == "report-writer":
            payload = json.loads(task_input)
            stats = payload["statistics"]
            answer = (call("format_document", {
                "title": "六个月销售简报（离线固定响应验证）",
                "summary": f"销售总额 {stats['total']} {payload['unit']}。",
                "findings": [
                    f"平均值 {stats['average']} {payload['unit']}。",
                    f"最高为 {stats['max_month']}，最低为 {stats['min_month']}。",
                    f"首末月变化 {stats['first_to_last_change_pct']}%，不代表同比。",
                ],
                "limitations": payload["source"] + "；" + payload["limitations"],
            }, "format") if not results else AIMessage(content=results[-1].content))
        else:
            step = len(results)
            if step == 0:
                answer = call("write_todos", {"todos": todos(["in_progress", "pending", "pending"])}, "plan1")
            elif step == 1:
                answer = call("task", {"subagent_type": "data-collector", "description": "读取完整六个月数据及单位和来源。"}, "collect")
            elif step == 2:
                answer = call("write_todos", {"todos": todos(["completed", "in_progress", "pending"])}, "plan2")
            elif step == 3:
                answer = call("task", {"subagent_type": "data-analyzer", "description": received("collect")}, "analyze")
            elif step == 4:
                answer = call("write_todos", {"todos": todos(["completed", "completed", "in_progress"])}, "plan3")
            elif step == 5:
                answer = call("task", {"subagent_type": "report-writer", "description": received("analyze")}, "write")
            elif step == 6:
                answer = call("write_todos", {"todos": todos(["completed"] * 3)}, "plan4")
            else:
                answer = AIMessage(content=received("write"))
        return ChatResult(generations=[ChatGeneration(message=answer)])


class MultiAgentTests(unittest.TestCase):
    def test_pipeline_and_context_boundaries(self):
        model = ScriptedModel()
        result = example.build_agent(model).invoke({
            "messages": [{"role": "user", "content": example.QUESTION + " USER_PRIVATE_MARKER"}],
        }, config={"recursion_limit": 60})
        calls = [c for m in result["messages"] for c in (getattr(m, "tool_calls", None) or [])]
        tasks = [c for c in calls if c["name"] == "task"]
        self.assertEqual([c["args"]["subagent_type"] for c in tasks],
                         ["data-collector", "data-analyzer", "report-writer"])
        self.assertEqual([c["name"] for c in calls],
                         ["write_todos", "task", "write_todos", "task", "write_todos", "task", "write_todos"])
        self.assertEqual([t["status"] for t in result["todos"]], ["completed"] * 3)
        self.assertEqual(json.loads(tasks[1]["args"]["description"])["sales"], [100, 120, 90, 150, 180, 210])
        self.assertEqual(json.loads(tasks[2]["args"]["description"])["statistics"]["total"], 850)
        self.assertIn("850", result["messages"][-1].text)
        self.assertIn("虚构教学数据", result["messages"][-1].text)

        expected_tools = {"data-collector": "read_sales_data", "data-analyzer": "statistical_analysis", "report-writer": "format_document"}
        self.assertEqual(len(model._seen), 14)
        for role, messages, tools in model._seen:
            if role == "supervisor":
                self.assertFalse(any(name in tools for name in expected_tools.values()))
                self.assertNotIn("data-collector: INTERNAL_STEP", str(messages))
                self.assertNotIn("data-analyzer: INTERNAL_STEP", str(messages))
                self.assertNotIn("report-writer: INTERNAL_STEP", str(messages))
            else:
                self.assertNotIn("USER_PRIVATE_MARKER", str(messages))
                self.assertEqual(len([m for m in messages if isinstance(m, HumanMessage)]), 1)
                self.assertIn(expected_tools[role], tools)
                self.assertNotIn("write_todos", tools)
                for other_role, name in expected_tools.items():
                    if other_role != role:
                        self.assertNotIn(name, tools)

    def test_statistics_and_zero_baseline(self):
        stats = example.statistical_analysis(["1月", "2月", "3月", "4月", "5月", "6月"], [100, 120, 90, 150, 180, 210])
        self.assertEqual(stats["total"], 850)
        self.assertEqual(stats["average"], 141.67)
        self.assertEqual(stats["first_to_last_change_pct"], 110)
        self.assertEqual(stats["min_month"], "3月")
        self.assertIsNone(example.statistical_analysis(["1月", "2月"], [0, 100])["first_to_last_change_pct"])

    def test_invalid_data(self):
        for months, values in (([], []), (["1月"], []), (["1月", "1月"], [1, 2]), (["1月"], [float("nan")]), (["1月"], [-1])):
            with self.subTest(months=months, values=values), self.assertRaises(ValueError):
                example.statistical_analysis(months, values)

    def test_analysis_failure_stops_before_writing(self):
        def statistical_analysis(months: list[str], sales: list[float]) -> dict:
            """模拟统计服务执行失败。"""
            raise RuntimeError("INJECTED_ANALYSIS_FAILURE")

        model = ScriptedModel()
        with patch.object(example, "statistical_analysis", statistical_analysis):
            agent = example.build_agent(model)
            with self.assertRaisesRegex(RuntimeError, "INJECTED_ANALYSIS_FAILURE"):
                agent.invoke({"messages": [{"role": "user", "content": example.QUESTION}]},
                             config={"recursion_limit": 60})
        self.assertNotIn("report-writer", [role for role, _, _ in model._seen])

    def test_missing_configuration(self):
        with patch.object(example, "dotenv_values", return_value={}), self.assertRaises(SystemExit):
            example.load_model()

    def test_entry_point_exports_actual_answer(self):
        with tempfile.TemporaryDirectory(prefix="ch05-multi-test-") as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            with patch.object(example, "PROJECT_DIR", root), patch.object(example, "load_model", return_value=ScriptedModel()), redirect_stdout(io.StringIO()):
                example.main()
            run_dirs = list((root / "runs").iterdir())
            self.assertEqual(len(run_dirs), 1)
            answer = (run_dirs[0] / "answer.md").read_text(encoding="utf-8")
            trace = json.loads((run_dirs[0] / "trace.json").read_text(encoding="utf-8"))
            self.assertEqual(answer, trace["messages"][-1]["content"])
            self.assertEqual(len(trace["task_calls"]), 3)
            self.assertIn("850", answer)


if __name__ == "__main__":
    print("固定响应离线验证：实际执行 Agent 图与工具，真实模型请求为 0。", flush=True)
    unittest.main(verbosity=2)
