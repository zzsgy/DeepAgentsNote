# 第三章可复现代码

## 两个入口，不混淆两种证据

| 入口 | 用途 | 是否需要密钥 | 本次提交验证范围 |
| --- | --- | --- | --- |
| `backend_compare.py` | 教程式真实模型实验，显式调用 LangChain / LangGraph / Deep Agents | 是 | 语法、导入、配置和四类 Agent 构造；尚无本次真实模型完整运行记录 |
| `verify_offline.py` | 确定性对照，检查真实文件工具和 Backend | 否 | 实际运行记录见 evidence，模型由本地 ScriptedToolModel 代替 |

真实模型示例来自学习过程中的手写版本，整理时移除了无用的 global/重复导入并补充类型标注。四个 Backend 分支和 `agent.invoke()` 都保留在主文件中，没有藏进 Driver。离线辅助测试才使用 Driver。

## 环境与安装

Python 3.12，deepagents 0.7.13。精确依赖与哈希见 `uv.lock`；第一次安装需要网络。以下命令在本 README 所在目录执行：

```powershell
uv sync --frozen --python 3.12
```

PyCharm：Open 本目录 → 设置中搜索 Python Interpreter → 选择现有解释器 `.venv\Scripts\python.exe`。
uv 的 hardlink 警告若随后显示 Installed，说明已回退复制成功，不是安装失败。

也可用 Python 3.12 虚拟环境安装导出的清单：

```powershell
python -m pip install -r requirements.txt
```

## A. 真实 deepseek-flash 教程实验

1. 将 `.env.example` 复制为 `.env`，只在本机填写新密钥和匹配的服务地址。若密钥曾公开到截图，应先撤销重发。
2. 三个名字必须一致：`OPENAI_API_KEY`、`OPENAI_API_BASE`、`MODEL_NAME`。默认模型别名为 `deepseek-flash`；不能据此假定任意服务商都支持它。服务地址、密钥与模型别名必须属于同一服务商配置。
3. 打开 `backend_compare.py`，修改顶部 `EXPERIMENT`，依次选择 `state`、`filesystem`、`store`、`composite`。
4. 右键 Run，或运行：

```powershell
uv run --frozen python backend_compare.py
```

程序明确展示：

- `ChatOpenAI`：LangChain 模型接入，兼容接口，不代表调用 OpenAI 官方模型。
- `InMemorySaver()`：LangGraph 的线程状态保存器。
- `InMemoryStore()`：LangGraph 的跨线程共享存储。
- `create_deep_agent(...)`：框架组装；`agent.invoke(...)`：真正运行。
- `RunnableConfig`：A/B 线程配置；`agent.get_state()`：检查真实 State。
- `ToolMessage`：实际工具返回；不能只看模型自述。

每个普通分支至少运行 A 写入、A 再读取、B 读取三轮；Composite 再对照临时路径。每轮可能调用模型多次，产生费用。此次整理没有读取本机真实密钥、没有代替用户发起外部模型请求。

将 PyCharm 控制台输出保存为本地文件后，先排除密钥、私人目录与服务信息，再补充真实模型实验记录。目前笔记明确保留该项待验证状态。

## B. 无密钥的重复验证

```powershell
uv run --frozen python verify_offline.py
uv run --frozen python verify_offline.py --only lifecycle
uv run --frozen python -m unittest -v
```

五组实验：tools、lifecycle、composite、permissions、policy。完整检查预期 85/85；`[PASS] 拒绝...` 意味着预期拒绝确实发生，不是操作获准。

它只替换模型的决策，不替换工具或后端。StateBackend 在真实 graph runtime 内运行；FilesystemBackend 确实落盘；StoreBackend 确实写入 Store。独立进程测试由固定 Python 探针完成，不使用 Agent Shell。

每次结果保存到新的 `runs/<编号>/REPORT.md` 和 `results.json`。所有失败会记录并返回退出码 1。无异常退出不等于实验完成，必须检查断言、工具结果和实际存储。

公开的[逐项报告](evidence/offline-report.md)和[工具调用原始记录（路径脱敏）](evidence/offline-results.json)可与源码逐项对应。发布自己的离线结果：

```powershell
uv run --frozen python publish_evidence.py runs/你的运行编号
```

此命令会更新本地 evidence 文件，不会自动提交或推送；它只替换绝对项目路径，不能当成通用的任意日志密钥清洗器。

## C. 预期结论与边界

| 配置 | 同线程下一轮 | 新线程 | 程序重启 |
| --- | --- | --- | --- |
| State + InMemorySaver | 能恢复 | 默认不能读取旧线程文件 | 内存 saver 丢失；持久化 saver 是另一个实验 |
| Filesystem，同一 root_dir | 可读 | 可读，不自动用户隔离 | 文件未删除则保留 |
| Store + 同一 InMemoryStore/namespace | 可读 | 可读 | 内存 Store 不保留 |
| Composite | 取决于路由 | 临时路径与 Store 路径不同 | 取决于路由及其底层存储 |

真实示例每次新建磁盘目录，避免覆盖旧记录；因此下次默认不会自动读取上次目录，但这不表示磁盘数据消失。

安全范围：

- 仅使用新建测试目录和假敏感资料；不提交 .env、IDE 配置、虚拟环境、截图或原始私人日志。
- 成功删除的只有本次创建的 disposable.txt。旧 runs 不自动删除。
- PolicyWrapper 是串行小文件教学实现，不提供生产事务锁，不保证全部符号链接风险已覆盖；不是 OS 沙箱。
- `virtual_mode=True` 是路径约束，不约束任意 Shell、网络或自定义工具。
- 本实验不证明上下文自动卸载、自动总结、多模态、HITL 或学习者独立掌握。

完整概念、报错复盘与学习心得见[第三章笔记](../../notes/ch03-virtual-filesystem.md)。
