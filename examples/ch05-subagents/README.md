# 第五章：多 Agent 协作示例

一个主协调者，通过 `task` 依次委派收集员、分析员、写作员。数据为六个月虚构销售额，不访问搜索服务、不使用真实企业数据。

## 文件与入口

| 文件 | 用途 |
|---|---|
| `multi_agent_example.py` | 完整单文件示例：工具、角色、主 Agent、配置、运行和导出 |
| `verify_multi_agents.py` | 固定响应模型驱动真实 Agent 图的 6 项离线测试 |
| `capture_offline.py` | 导出一次离线协作的任务、统计结果和报告 |
| `reports/` | 本次离线运行记录；不是远端模型成功证明 |
| `.env.example` | 真实模型入口所需的三个配置项，不包含凭证 |

## 安装与离线验证

在本目录打开终端，安装 uv 后运行：

```powershell
uv sync --frozen
uv run --frozen python -X utf8 verify_multi_agents.py
uv run --frozen python -X utf8 capture_offline.py
```

依赖安装可能需要联网；测试和捕获脚本不读取 `.env`，用审计钩子拒绝 socket 连接和地址解析，不发出远端模型或搜索请求。Python 固定为 3.12 系列，Deep Agents 固定为 0.7.13；其他版本见锁文件。沿用本章锁文件中的 Tavily 依赖，但本销售示例不使用它，也不要求 Tavily Key。

## PyCharm 真实模型运行

1. 打开本目录并完成 `uv sync --frozen`。
2. 选择本目录生成的 `.venv/Scripts/python.exe` 作为解释器，不使用其他项目的解释器。
3. 复制 `.env.example` 为 `.env`，填写模型名、OpenAI-compatible 接口地址和 API Key。模型及接口需要支持工具调用。
4. 直接运行 `multi_agent_example.py`。
5. 查看控制台三个业务工具的执行信息、主 Agent 委派参数、Todo 和最终报告。
6. 运行完成后查看 `runs/multi-*/answer.md` 与 `trace.json`。该记录包含父消息和委派，不是子 Agent 内部全部消息。

真实运行会调用用户配置的服务，产生相应 API 消耗。本次提交没有执行真实模型入口；离线结果不能证明该服务的鉴权、工具兼容性或自主委派质量。

## 预期业务结果与边界

输入销售额：`100, 120, 90, 150, 180, 210`，单位万元。

- 总额 850，均值 141.67。
- 最高 6 月 210，最低 3 月 90。
- 首末月变化 110%，不是同比；首月为零时比例返回 `null`。
- 没有成本、利润、去年同期或市场活动数据，不做相关推断。

`subagents` 清单不会强制执行顺序，Todo 也不是调度器。真实入口依靠提示词引导；离线模型通过固定规则产生委派。业务工具分工不等于完整权限沙箱，默认通用子 Agent 和框架内置能力仍存在。

建议独立练习：修改一项销售额并核对指标；将首月改成零；删除一次委派中的 `sales` 并观察失败位置。完成这些练习后再评价自己的独立实现和调试能力。

[完整学习笔记](../../notes/ch05-subagents.md) · [运行记录](reports/verification.md)
