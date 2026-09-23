# 第四章离线验证记录

- 验证日期：2026-09-23。
- 执行者：Codex 辅助验证；不是学习者独立考核。
- 环境：原生 Windows，CPython 3.12.13，独立 `.venv`。
- 依赖：按本目录 `uv.lock` 安装；Deep Agents 0.7.13、LangChain 1.4.2、LangGraph 1.2.11。
- 真实模型请求：0；Tavily 请求：0。测试脚本阻断 socket 连接与 DNS 查询。

## 复现命令

从 `examples/ch04-task-planning` 执行：

```powershell
uv sync --frozen --python 3.12
uv run --frozen python -X utf8 verify_offline.py
```

首次建环境时使用 `uv sync --python 3.12` 生成锁文件，解析 63 个包并安装 61 个包。后续按锁文件复现。

## 本次独立环境的实际输出

```text
test_checkpoint_and_thread_isolation (__main__.Chapter4Tests.test_checkpoint_and_thread_isolation) ... ok
test_missing_config_fails_locally (__main__.Chapter4Tests.test_missing_config_fails_locally) ... ok
test_missing_file_is_not_completion (__main__.Chapter4Tests.test_missing_file_is_not_completion) ... ok
test_summary_preserves_todos_and_history (__main__.Chapter4Tests.test_summary_preserves_todos_and_history) ... ok
test_todos_replace_entire_list (__main__.Chapter4Tests.test_todos_replace_entire_list) ... ok
test_workflow_and_export (__main__.Chapter4Tests.test_workflow_and_export) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.453s

OK
```

时间是本次测试套件测得的运行时间，不是学习者学习用时，也不是性能评测。

## 观察与断言

| 测试 | 实际验证的行为 |
|---|---|
| 主流程 | 7 次工具调用都有响应，3 次 Todo 更新，报告写入与读回，导出文本精确一致 |
| 整体替换 | 原有 3 个 Todo 被新提交的单条清单替换，不会自动追加 |
| 线程 | 同一 `thread_id` 保留清单及文件，新线程没有旧清单与文件 |
| 缺文件 | 收到 not found 内容，未产生报告，不把未完成清单当成功 |
| 摘要 | 实际产生摘要事件，保留 todos，模型消息数减少，历史内容能读回 |
| 缺配置 | 没有当前项目 .env 时明确失败，不使用环境变量作为隐式替代配置 |

主流程中的模型行为由测试预先规定：

```text
write_todos  [in_progress, pending, pending]
internet_search  固定测试资料，不联网
write_file  /notes.md
write_todos  [completed, in_progress, pending]
write_file  /final_report.md
read_file   /final_report.md
write_todos  [completed, completed, completed]
```

读写报告的固定内容为：

```markdown
# 离线测试报告

固定文本，仅验证工具连接，不是实时研究。
```

这段轨迹是实际执行的**脚本测试轨迹**，不是模型自行生成的计划。测试中的导出文件位于临时目录，断言完成后由临时目录机制清理；不会留下一份假装联网调研的最终报告。

## 没有证明的事项

- 真实模型能否自主拆解和持续更新计划。
- 本机真实模型端点与 Tavily API Key 是否有效。
- 三种 Harness 的最新能力、优劣和事实结论。
- 进程重启或数据库持久化恢复。
- 学习者独立实现、故障排查和延迟复测是否通过。

用户此前的联网运行出现 Tavily `InvalidAPIKeyError`。本次没有用离线结果覆盖这一事实，真实成功记录仍待补充。
