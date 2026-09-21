# 第三章：虚拟文件系统与 Context Engineering

整理日期：2026-09-21。

本章作业包含文件系统实验记录、Backend 对比结论和可复现代码。本文区分课程机制、实际测试结果与尚未验证的内容，不把复制示例或测试通过等同于独立掌握。

## 1. 作业入口与验证范围

| 内容 | 入口 |
| --- | --- |
| PyCharm 操作、环境安装和运行说明 | [实验 README](../examples/ch03-virtual-filesystem/README.md) |
| 真实模型四组对比代码 | [backend_compare.py](../examples/ch03-virtual-filesystem/backend_compare.py) |
| LangChain 模型配置 | [model_config.py](../examples/ch03-virtual-filesystem/model_config.py) |
| 无 API Key 的可重复验证 | [verify_offline.py](../examples/ch03-virtual-filesystem/verify_offline.py) |
| 实际输出与检查项 | [脱敏实验报告](../examples/ch03-virtual-filesystem/evidence/offline-report.md) |
| 机器可读实验结果 | [offline-results.json](../examples/ch03-virtual-filesystem/evidence/offline-results.json) |

这次在独立环境中执行了真实 Deep Agents 文件工具及 Backend，离线验证为 **85/85 项通过**，另有 **5 项 unittest 测试通过**。离线驱动用脚本指定工具调用，避免模型随机选择工具，**不是自己模拟 Backend 实现**。

真实模型版显式使用 `ChatOpenAI`、`create_deep_agent`、`InMemorySaver`、`InMemoryStore` 和 `agent.invoke()`，已检查四种 Agent 的构造；本次没有发起付费模型调用，四组真实模型端到端运行仍待验证。真实模型输出、学习者独立调试和延迟复测均不在上述通过数中。

## 2. 我对虚拟文件系统的理解

虚拟文件系统提供统一的文件路径和操作接口。Agent 使用相同的 `read_file`、`write_file`、`edit_file`、`ls`、`glob`、`grep`，背后可以连接不同存储。

这里的“虚拟”不代表文件一定在内存里，也不代表一定是操作系统上的真实文件。例如，同一个 `/notes/demo.md` 可以是 Agent State 中的一项数据，也可以映射到本地目录中的真实文件。

需要分清三个层次：

| 层次 | 职责 | 本实验中的例子 |
| --- | --- | --- |
| 模型 | 根据任务提出工具调用 | `ChatOpenAI` 对接兼容接口；离线版用确定性工具调用驱动 |
| 工具与运行框架 | 校验、执行工具调用，推进流程，传递状态 | Deep Agents 工具、LangGraph 执行与 Checkpointer |
| 存储后端 | 决定文件内容存在哪里、如何读写 | State、Filesystem、Store、Composite |

开发者配置模型、Backend、权限和运行环境；模型在运行时选择调用工具；工具的 Python 实现真正执行操作。因此，模型“说已经保存”不是证据，还需要查看工具结果与实际存储。

### 结构化存储与非结构化内容

结构化数据有明确字段和类型，例如实验结果中的 `name`、`passed`、`detail`。自然语言报告、图片等内容则通常没有固定表格字段。二者可以共存：一篇自由文本笔记可以作为结构化记录的 `content` 字段保存。

把 Markdown 文件分类放进目录，是有组织地管理内容，不等于把正文自动变成数据库表。文件路径、内容格式、底层存储介质是不同概念。

### 为什么它属于上下文工程

模型每次能处理的上下文有限。把所有历史和工具输出不断堆进消息，会增加成本，也会使有效信息更难定位。

课程介绍了两类机制：大工具结果保存为文件，消息中留下引用与预览；对话过长时生成摘要，同时保留可回溯记录。Agent 再通过搜索和分片读取获取必要细节。

这与普通“保存文件”的区别在于：文件承担上下文外部存储的角色。保存了不等于模型当前已经读到，摘要也不能保证完全保留原文信息。

本实验没有测量自动卸载、自动总结的触发阈值，也没有验证多模态读取；教程中的 token 数、窗口比例和格式支持不能当作本次实测结论。

## 3. 工具实验：读取、搜索与修改

对 StateBackend、FilesystemBackend、StoreBackend 使用同样的四行测试文本：

```text
第1行：学习 Backend
第2行：TODO 阅读
第3行：TODO 实验
第4行：完成
```

| 操作 | 实际观察 |
| --- | --- |
| `write_file` 后 `read_file` | 能读回四行内容 |
| `offset=1, limit=2` | 读到第 2、3 行；本版本 offset 从 0 开始 |
| `ls`、`glob` | 能定位 `/notes/demo.md` |
| `grep` 的 `files_with_matches` | 返回包含 TODO 的文件路径 |
| `grep` 的 `content` | 返回第 2、3 行的匹配内容 |
| `grep` 的 `count` | 本样本输出 `/notes/demo.md: 2` |
| 将一个 TODO 替换为 DONE | 重新读取后确认内容改变 |
| 替换不存在的字符串 | 返回错误，原文未改变 |
| 再次写入同一路径 | 在锁定的 0.7.13 版本中覆盖原文，不是追加 |
| 删除可丢弃测试文件 | 再读返回不存在 |

分片读取的实际输出包括：

```text
2  第2行：TODO 阅读
3  第3行：TODO 实验

[Read 2 lines (lines 2-3 of 4 total). 1 line remaining from offset 3.]
```

所以，“工具执行成功”不能直接推导为“已经读完全部内容”。分页或截断时应继续读取，搜索范围过大时应缩小路径与条件。

## 4. Backend 对比设计与记录

### 实验方法

控制条件包括相同依赖版本、相同文件内容、相同工具操作。主要变化是 Backend、thread_id、Checkpointer、Store 实例、namespace 和磁盘根目录。

运行环境：Python 3.12.13，deepagents 0.7.13，langchain 1.4.2，langchain-core 1.6.3，langgraph 1.2.11。完整依赖固定在 `uv.lock`，安装导出记录见 `requirements.txt`。

| 检查组 | 通过数 | 覆盖内容 |
| --- | ---: | --- |
| 文件工具 | 42/42 | 三种后端的读写、搜索、编辑、负例和存储检查 |
| 生命周期 | 12/12 | 同线程、新线程、新 Agent、不同存储实例、新 Python 进程 |
| 混合路由 | 9/9 | 默认路由、路径前缀、跨线程、聚合搜索与路径拼写错误 |
| 声明式权限 | 11/11 | 只读、拒绝、规则顺序、默认行为和越界路径 |
| 自定义策略包装器 | 11/11 | 写入大小、编辑后大小、保护目录、审计和路由组合 |
| 合计 | **85/85** | 逐项原始观察见实验报告 |

### StateBackend：线程中的工作文件

实验观察：同一个 thread_id 配合同一个 Checkpointer，可以在后续调用中找回文件；换成新线程 B，读不到 A 的文件。新建 Agent 但复用同一个 Checkpointer 和线程，仍可恢复；换成新的内存 Checkpointer，就没有原记录。

结论：StateBackend 与 LangGraph State 相关，文件随线程状态管理。Checkpointer 负责保存与恢复状态，但不会自动让新线程共享旧线程文件。

不能简单说“对话结束立即删除”。是否能在进程重启后恢复，还取决于 Checkpointer 是否真正持久化。本实验使用 `InMemorySaver`，不具备跨进程持久化。

### FilesystemBackend：真实磁盘文件

实验观察：文件确实出现在专用实验目录；新线程、新 Agent 在使用同一磁盘根目录时可以读取；另起 Python 进程仍能读取。

结论：保存范围由真实目录决定，不以 thread_id 为隔离边界。适合需要保留输出文件的本地任务，但权限设置错误会影响真实数据。

`virtual_mode=True` 是文件路径约束，不等于容器或操作系统沙箱，不能用它来保证任意 Shell、自定义工具或网络访问被隔离。本作业不使用 LocalShellBackend。

### StoreBackend：跨线程共享

实验观察：相同 Store 实例、相同 namespace 下，新线程可以读取文件；更换 namespace 后不可见。新 Agent 复用原 Store 可读；换成全新的 `InMemoryStore()` 不可读。

结论：“跨会话”与“程序重启后仍保存”是两回事。`InMemoryStore` 便于开发阶段验证跨线程行为，但仍是进程内存。长期持久化需要持久化 Store 实现及其正确配置。

namespace 是数据分区；生产中的用户身份应来自可信身份认证，不能把用户自行提供的字符串当作完整授权机制。

### CompositeBackend：按路径分配存储

实验配置采用默认 State，并把特定前缀路由到磁盘与 Store。观察到：默认路径仍在线程 State 中；Store 路由可以跨线程；磁盘路由映射到真实文件；聚合搜索保留外部路径前缀。

一个容易忽略的负例是把 `/memories/` 写成 `/memory/`：路径未匹配目标路由，会落到默认 State，而不是自动纠正或自动拒绝。需要用实际存储与新线程读取验证去向。

CompositeBackend 的路径路由与权限规则不是同一种匹配逻辑：后端路由按路径前缀选择，权限规则按其规则顺序检查。配置时不要混为一谈。

### 对比结论

| 后端及实验配置 | 同线程续用 | 新线程共享 | 新进程恢复 | 适合用途 |
| --- | --- | --- | --- | --- |
| State + InMemorySaver | 是，需复用保存器 | 否 | 否 | 任务草稿、中间结果 |
| Filesystem，同一根目录 | 是 | 是 | 是，文件仍在时 | 本地报告与项目文件 |
| Store + 同一 InMemoryStore/namespace | 是 | 是 | 否 | 开发阶段跨线程记忆验证 |
| Composite | 取决于命中的后端 | 取决于命中的后端 | 取决于命中的后端 | 草稿、长期记忆和磁盘输出混合管理 |

没有一种后端在所有场景都最好。选择前应先回答：需要保存多久？谁可以共享？存储是否跨进程？如何隔离用户？是否会修改真实文件？

## 5. 权限与安全策略实验

声明式权限实验验证了拒绝敏感测试文件读取、禁止写入/编辑/删除、规则顺序以及未匹配规则时的行为。锁定版本中的 first-match 与默认允许行为提示我：不能只列出几条拒绝规则，就假定其他路径也被拒绝；需要明确配置兜底规则，并测试负例。

本作业另提供 [lab/policy.py](../examples/ch03-virtual-filesystem/lab/policy.py) 中的自定义 PolicyWrapper。它不是声称框架自动提供的万能沙箱，而是对 Backend 操作添加具体约束：

- 小样本最大内容为 80 字节，81 字节写入被拒绝，原数据保持不变。
- 编辑按“编辑后的完整内容”检查，避免只检查替换片段而漏掉总量超限。
- 保护目录需要覆盖目录本身、子路径以及父目录操作的影响。
- 审计只记录动作、路径与结果，不把正文或密钥写进日志。

这些测试是串行、受控夹具验证，不覆盖并发竞态、生产授权体系或任意 Shell 执行。所有越界、敏感文件与删除用例使用专用实验夹具，不涉及真实密钥或用户文件。

## 6. 如何复现

克隆仓库后，在 `examples/ch03-virtual-filesystem` 打开终端：

```powershell
uv sync --frozen --python 3.12
uv run --frozen python -X utf8 verify_offline.py
uv run --frozen python -X utf8 -m unittest -v
```

本次上述命令实际得到：

```text
85/85 检查通过
Ran 5 tests in 8.566s
OK
```

运行耗时会随机器变化。输出保存在每次新建的 `runs/<运行编号>/`，不会自动清理过去的数据。新进程测试验证的是同一测试目录，而不是下一次实验创建的另一个目录。

真实模型版本：将 `.env.example` 复制为本地 `.env`，填写提供方匹配的 API 地址、模型名和新密钥；在 PyCharm 选择本目录 `.venv/Scripts/python.exe`；依次把 `EXPERIMENT` 改为 `state`、`filesystem`、`store`、`composite`，运行 `backend_compare.py`。配置保留用户选择的 `deepseek-flash`，但是否支持该名称必须由实际 API 提供方确认。

真实模型执行涉及 API 费用。每组都应检查工具调用、存储内容与跨线程结果，不要仅根据最终自然语言回答判定成功。完整操作步骤见实验 README。

## 7. 本次调试中学到的事

| 现象 | 原因或检查重点 |
| --- | --- |
| uv 提示 hardlink 失败 | 如果后面已安装成功，这是退回复制的警告，不等于依赖安装失败 |
| `.env` 填了地址仍提示缺失 | `OPENAI_API_URL` 与 `OPENAI_API_BASE` 不同；读取名、示例名、报错信息必须一致 |
| API Key 参数有类型提示 | 区分 IDE 静态检查和运行异常；示例显式使用 `SecretStr` |
| Checkpointer 类型不匹配 | `InMemorySaver` 是类，`InMemorySaver()` 才是实例 |
| 退出码 0 却没有实验输出 | 可能只定义函数，没有执行 `if __name__ == "__main__": main()`；退出成功不等于任务完成 |
| config 有 TypedDict 提示 | 用 `RunnableConfig` 注解配置，避免让 IDE 只推断成普通嵌套 dict |
| 代码有颜色或波浪线 | 先看悬浮检查内容，再看运行 traceback，不能只凭颜色判断 |
| 截图含密钥 | 立即撤销并更换，不应继续传播截图；仓库只放空白 `.env.example` |

本次发布不包含 `.env`、API Key、截图、虚拟环境和原始本机路径。已提交的实验输出使用 `<LAB_ROOT>` 代替本机根路径。

## 8. 学习心得与课程反馈

### 学习心得

学习第三章后，我对 Agent 文件系统的理解从“让模型读写文件”，转变为“用统一工具管理任务资料，并按需要把信息移入、移出上下文”。我初步分清了临时 State、真实磁盘、跨线程 Store 与混合路由，也认识到跨线程共享不等于跨进程持久化。

在 PyCharm 配置和调试过程中，我发现环境变量命名、对象实例化、程序入口和类型提示都会影响实验推进。以后判断实验是否成功，我会同时检查工具调用、实际存储和负例，而不只看退出码或模型的回答。目前仍需自己完成真实模型四组实验，并独立修改用例验证理解。

### 课程反馈

课程把文件工具、上下文管理、存储后端和权限结合起来，有助于理解 Agent 为什么需要外部工作空间。建议补充一套固定依赖版本的 Windows/PyCharm 最小完整项目，让初学者能从解释器配置、环境变量到运行结果逐步核对。

也建议更明确地区分 State、Checkpointer、Store 的职责，尤其是“换线程”“换 Agent”“重启进程”三个实验条件；为每种 Backend 提供预期输出和反例，并标明 API 版本差异。安全章节可以进一步对照路径约束、权限规则与真正执行沙箱的边界，避免把局部限制误当成完整隔离。

## 9. 待独立完成的验收

这些不是已完成声明，而是下一步检查清单：

- 不看笔记解释：为什么新 thread_id 读不到 State 文件，而同 namespace 的 Store 可以？
- 先预测，再运行四组真实模型实验，保存脱敏工具输出。
- 把 Composite 的记忆前缀改名，验证正确路径与拼错路径分别落到哪里。
- 加一个权限拒绝用例，证明失败后原文件不变。
- 至少两天后重新解释生命周期，并独立修复一个配置错误，再评价掌握程度。

## 参考资料

- [Datawhale 第三章：虚拟文件系统](https://datawhalechina.github.io/deepagents-in-action/chapters/ch03-virtual-filesystem/)
- [Deep Agents 官方 Backends 文档](https://docs.langchain.com/oss/python/deepagents/backends)
- [LangGraph 官方持久化文档](https://docs.langchain.com/oss/python/langgraph/persistence)

官方文档可能随版本变化；本作业的实测结论以锁定依赖、实验条件和随附输出为准。
