"""第五章：主 Agent 协调收集、分析、写作三个专业子 Agent。

真实运行：在 PyCharm 中直接运行本文件，读取同目录 .env。
离线验证：运行 verify_multi_agents.py（固定响应，不验证真实模型能力）。
"""

import json
import math
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from deepagents import create_deep_agent
from dotenv import dotenv_values
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI


PROJECT_DIR = Path(__file__).resolve().parent
QUESTION = "分析本地虚构的六个月销售数据，计算总额、均值、最高最低月份及首末月变化，写一份中文简报。"


# 1. 业务工具：每个子 Agent 只配置自己职责所需的业务工具。
def read_sales_data() -> dict:
    """读取固定教学数据，返回月份、销售额、单位、来源和数据局限。"""
    print("[data-collector 工具] 读取虚构销售数据", flush=True)
    return {
        "months": ["1月", "2月", "3月", "4月", "5月", "6月"],
        "sales": [100, 120, 90, 150, 180, 210],
        "unit": "万元",
        "source": "本脚本内置的虚构教学数据，不是真实企业数据",
        "limitations": "只有六个月销售额，没有成本、利润、去年同期或市场活动数据。",
    }


def statistical_analysis(months: list[str], sales: list[float]) -> dict:
    """计算按时间顺序排列的月度销售额；月份和数值必须等长且非空。"""
    if not months or len(months) != len(sales):
        raise ValueError("月份和销售额必须等长且非空，不能用空数据继续分析。")
    if any(not month.strip() for month in months) or len(set(months)) != len(months):
        raise ValueError("月份不能为空或重复。")
    if any(not math.isfinite(value) or value < 0 for value in sales):
        raise ValueError("本例销售额必须是有限的非负数。")

    print("[data-analyzer 工具] 使用 Python 计算统计指标", flush=True)
    maximum = max(range(len(sales)), key=sales.__getitem__)
    minimum = min(range(len(sales)), key=sales.__getitem__)
    total = math.fsum(sales)
    return {
        "count": len(sales),
        "total": round(total, 2),
        "average": round(total / len(sales), 2),
        "max_month": months[maximum],
        "max_sales": sales[maximum],
        "min_month": months[minimum],
        "min_sales": sales[minimum],
        "first_to_last_change_pct": (
            round((sales[-1] - sales[0]) / sales[0] * 100, 2)
            if sales[0] != 0 else None
        ),
        "note": "首末月变化不是同比；首月为 0 时比例为 null；最高最低并列时返回首次出现月份。",
    }


def format_document(title: str, summary: str, findings: list[str], limitations: str) -> str:
    """将已核对的摘要、发现和局限排成 Markdown；只返回文本，不写磁盘。"""
    if not title.strip() or not summary.strip() or not findings or not limitations.strip():
        raise ValueError("报告必须包含标题、摘要、发现和局限。")
    print("[report-writer 工具] 整理 Markdown 报告", flush=True)
    bullets = "\n".join(f"- {item}" for item in findings)
    return (
        f"# {title}\n\n> 虚构教学数据，不是真实业务报告。\n\n"
        f"## 摘要\n\n{summary}\n\n## 关键发现\n\n{bullets}\n\n"
        f"## 数据来源与局限\n\n{limitations}\n"
    )


# 2. 子 Agent 清单是能力登记表；列表顺序不会强制执行顺序。
def build_agent(model):
    subagents = [
        {
            "name": "data-collector",
            "description": "读取本地虚构销售数据，返回完整的月份、数值、单位和来源；不做统计或写报告。",
            "system_prompt": """你是数据收集员 data-collector。
必须调用 read_sales_data。返回它提供的完整数据，保留 months、sales、unit、source、limitations。
六条记录很小，必须逐项保留，不能只说“销售额整体上升”。返回 JSON 文本，不加代码围栏。
工具失败就如实报告失败，禁止编造或补齐数据。""",
            "tools": [read_sales_data],
        },
        {
            "name": "data-analyzer",
            "description": "分析委派说明中明确提供的月份和销售额，调用统计工具，返回统计指标及局限。",
            "system_prompt": """你是数据分析员 data-analyzer。
从本次委派说明取得完整 months、sales、单位和来源，调用 statistical_analysis。
保留全部计算结果，以 JSON 文本返回，并附原始单位、来源和局限，不加代码围栏。
不要假定能看到收集员的聊天记录。输入缺失或工具失败时，明确报告并请求重新提供数据。
不要自己估算数字，不把首末月变化称为同比，也不推断没有证据的增长原因。""",
            "tools": [statistical_analysis],
        },
        {
            "name": "report-writer",
            "description": "根据明确提供的统计结果、单位和来源写中文简报，使用排版工具；不重新搜集或计算数据。",
            "system_prompt": """你是报告写作员 report-writer。
只能使用本次委派说明中提供的已核对指标，调用 format_document 生成中文 Markdown 报告。
报告包含摘要、3—5 条关键发现、来源与局限，并明确是虚构教学数据。
不能编造原因、同比、利润或外部来源；缺少统计结果时先报告问题，不写伪完整报告。
最终回答原样返回 format_document 的报告文本。""",
            "tools": [format_document],
        },
    ]

    # 3. 主 Agent 显式启用 Todo。子 Agent 不需要继承这份主任务清单。
    return create_deep_agent(
        model=model,
        middleware=[TodoListMiddleware()],
        system_prompt="""你是项目协调者，负责这次虚构数据简报。
1. 调用 write_todos 制定“收集数据、分析数据、编写报告”三步计划。
2. 用 task 委派给 data-collector，取得完整数据与单位、来源。
3. 检查返回内容，成功后更新计划。把收集结果完整写入下一次 task 的 description，委派给 data-analyzer。
4. 检查统计结果，成功后更新计划。把指标、单位、来源和局限完整写入下一次 description，委派给 report-writer。
5. 检查报告与指标是否一致，确认后再标记全部完成，并输出完整报告。
每次 write_todos 都提交整份清单。每轮最多发起一个 task，等上一步返回再进行有依赖的下一步。
三个专业角色通过你传递结果，不会自动看到彼此的消息。不要用“按上文”代替实际数据。
本次只委派给上述三个角色，不使用 general-purpose，不用文件或执行工具绕过业务工具。
如果某步失败、缺数据或结果不一致，不要把该步标记完成，不得继续用猜测的数据写报告；说明失败位置。
这些要求是模型指令；不得宣称只写了 Todo 就已经完成工作。""",
        subagents=subagents,
    )


def load_model():
    """只读取同目录 .env；本例不需要 Tavily。"""
    config = dotenv_values(PROJECT_DIR / ".env", interpolate=False)
    required = ("MODEL_NAME", "OPENAI_API_BASE", "OPENAI_API_KEY")
    missing = [name for name in required if not (config.get(name) or "").strip()]
    if missing:
        raise SystemExit("请填写本脚本同目录 .env：" + ", ".join(missing))
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    return ChatOpenAI(
        model=config["MODEL_NAME"],
        api_key=config["OPENAI_API_KEY"],
        base_url=config["OPENAI_API_BASE"],
        use_responses_api=False,
        timeout=60,
        max_retries=1,
    )


def main():
    agent = build_agent(load_model())
    print("开始运行：真实模型 + 本地虚构数据。等待主 Agent 分配任务……", flush=True)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": QUESTION}]},
        config={"recursion_limit": 60},
    )

    # 4. 观察父 messages：可以看到委派任务与回传，但看不到子 Agent 完整工具消息。
    task_calls = [
        call for message in result["messages"]
        for call in (getattr(message, "tool_calls", None) or [])
        if call["name"] == "task"
    ]
    print("\n=== 主 Agent 的委派记录 ===")
    for index, call in enumerate(task_calls, 1):
        print(f"{index}. {call['args'].get('subagent_type')}")
        print(call["args"].get("description", ""))
    names = [call["args"].get("subagent_type") for call in task_calls]
    if names != ["data-collector", "data-analyzer", "report-writer"]:
        print("[观察] 委派轨迹与三步示例不完全一致，请检查是否遗漏、重复或重试。")

    print("\n=== 最终 Todo 状态（状态声明，不等于业务验收） ===")
    print(json.dumps(result.get("todos", []), ensure_ascii=False, indent=2))
    final_text = next(
        (m.text for m in reversed(result["messages"]) if isinstance(m, AIMessage) and m.text),
        "没有获得文本回答。",
    )
    print("\n=== 最终回答 ===\n" + final_text)

    # 主程序固定导出，不让模型决定 Windows 文件路径；每次使用新目录。
    run_dir = PROJECT_DIR / "runs" / ("multi-" + datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8])
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "answer.md").write_text(final_text, encoding="utf-8")
    (run_dir / "trace.json").write_text(json.dumps({
        "mode": "live-model-local-fictional-data",
        "task_calls": task_calls,
        "todos": result.get("todos", []),
        "messages": [m.model_dump(mode="json") for m in result["messages"]],
        "note": "记录模型实际输出，未自动证明报告正确或学习者掌握。",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n回答与主 Agent 消息记录已保存：", run_dir)


if __name__ == "__main__":
    main()
