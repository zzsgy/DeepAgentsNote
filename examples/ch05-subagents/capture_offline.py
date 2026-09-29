"""记录真实图执行、固定模型响应的离线结果；不代表自主模型能力。"""

import json
from pathlib import Path

# 导入时安装拒绝网络的审计钩子；不会读取 .env。
from verify_multi_agents import ScriptedModel
import multi_agent_example as example


def main():
    model = ScriptedModel()
    result = example.build_agent(model).invoke(
        {"messages": [{"role": "user", "content": example.QUESTION}]},
        config={"recursion_limit": 60},
    )
    calls = [call for message in result["messages"]
             for call in (getattr(message, "tool_calls", None) or [])]
    tasks = [call for call in calls if call["name"] == "task"]
    assert [call["args"]["subagent_type"] for call in tasks] == [
        "data-collector", "data-analyzer", "report-writer",
    ]
    analysis = json.loads(tasks[2]["args"]["description"])
    assert analysis["statistics"]["total"] == 850
    report = result["messages"][-1].text
    assert "850" in report and "虚构教学数据" in report
    payload = {
        "mode": "offline-scripted-model-real-graph",
        "remote_model_requests": 0,
        "scripted_model_calls": len(model._seen),
        "parent_tool_sequence": [call["name"] for call in calls],
        "delegations": [call["args"] for call in tasks],
        "analysis": analysis,
        "todos": result["todos"],
        "scope": "Fixed responses exercise the actual graph and tools; no live-model capability claim.",
    }
    output = Path(__file__).resolve().parent / "reports"
    output.mkdir(exist_ok=True)
    (output / "offline-run.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    (output / "offline-report.md").write_text(report, encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(report)


if __name__ == "__main__":
    main()
