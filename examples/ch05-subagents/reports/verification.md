# 第五章离线运行记录

验证日期：2026-09-29。环境：Windows、Python 3.12.13、Deep Agents 0.7.13，完整依赖由 `uv.lock` 固定。

## 运行命令与输出

在 `examples/ch05-subagents` 目录运行：

```powershell
uv sync --frozen
uv run --frozen python -X utf8 verify_multi_agents.py
uv run --frozen python -X utf8 capture_offline.py
```

依赖安装成功；测试输出：

```text
test_analysis_failure_stops_before_writing ... ok
test_entry_point_exports_actual_answer ... ok
test_invalid_data ... ok
test_missing_configuration ... ok
test_pipeline_and_context_boundaries ... ok
test_statistics_and_zero_baseline ... ok
Ran 6 tests in 0.601s
OK
```

## 验证内容

| 验证项 | 实际观察 |
|---|---|
| 委派顺序 | data-collector → data-analyzer → report-writer |
| 计划状态 | 四次 write_todos，最终三项 completed；业务指标另有断言 |
| 固定模型调用 | 14 次；远端模型请求为 0 |
| 数据转交 | 分析任务含完整六项销售额，写作任务含总额 850 等统计结果 |
| 消息隔离 | 父用户测试标记未进入子消息；子内部步骤未进入父消息 |
| 工具分工 | 专业角色得到对应业务工具，没有其他专业业务工具或主 Todo |
| 数值边界 | 空数据、长度错配、重复月份、NaN、负数被拒绝；首月零时比例为空 |
| 工具异常 | 注入统计 RuntimeError，invoke 抛出异常，写作员未执行 |
| 配置缺失 | 缺模型配置时入口退出，不请求远端服务 |
| 报告导出 | 临时运行目录的 answer.md 与父消息最终文本一致 |

实际捕获：[委派与结果 JSON](offline-run.json)、[离线报告](offline-report.md)。捕获脚本用同一测试模型运行实际图，并对角色顺序、总额和报告内容做断言。

## 证据范围

测试和捕获脚本不读取真实 `.env`，拒绝 socket 连接与地址解析。安装依赖不属于离线执行部分。

这是固定规则产生工具调用的测试模型，不是远端 LLM。调用真实框架和工具验证了给定轨迹下的行为，不能证明真实模型会正确路由、准确传参或生成正确报告。没有执行真实模型入口，没有操作 PyCharm GUI，也没有验证学习者独立实现或延迟复测。

这些结果不证明所有自定义状态完全隔离，工具分工也不代表权限沙箱。首末月变化不是同比，数据不足以推断利润或增长原因。
