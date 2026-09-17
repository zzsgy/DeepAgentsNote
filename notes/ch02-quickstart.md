# 第二章：从最小 Deep Agent 到工具调用与 LangSmith 追踪

> 学习日期：2026-09-16 至 2026-09-17  
> 课程章节：[Deep Agents 实战 · 第二章 Quickstart](https://datawhalechina.github.io/deepagents-in-action/chapters/ch02-quickstart/)  
> 实践环境：Windows、VS Code、Python 3.12、Deep Agents 0.7、LangChain 1.x、DeepSeek OpenAI-compatible 接口、Tavily、LangSmith  
> 当前结论：示例已经完成本地运行和 Trace 观察；本笔记记录的是理解与实践结果，不代表相关能力已经通过独立实现和延迟复测。

## 1. 本章学习目标

第二章的核心不是背诵一个 API，而是建立最小 Deep Agent 的完整心智模型：

1. 使用 `ChatOpenAI` 接入支持 Tool Calling 的聊天模型。
2. 把普通 Python 函数注册成 Agent 工具。
3. 使用 `system_prompt` 定义 Agent 的角色和工作边界。
4. 使用 `TodoListMiddleware` 为复杂任务增加计划能力。
5. 区分 `create_deep_agent()` 的组装阶段和 `agent.invoke()` 的运行阶段。
6. 使用 LangSmith 查看模型、工具和状态的调用链。
7. 根据报错判断问题发生在导入、配置、Agent 组装还是运行阶段。

## 2. 最小 Deep Agent 的组成

| 组成部分 | 代码位置 | 职责 |
|---|---|---|
| 模型 | `ChatOpenAI(...)` | 理解问题、决定是否调用工具、生成回答 |
| 工具 | `internet_search(...)` | 真正执行搜索等外部动作 |
| 系统提示词 | `system_prompt=...` | 定义角色、任务目标和行为边界 |
| Agent Harness | `create_deep_agent(...)` | 连接模型、工具、中间件和执行循环 |

最重要的边界是：

> 模型不会直接执行本地 Python 函数。模型产生结构化的 Tool Call；Deep Agent 解析调用请求、执行 Python 函数，再把工具结果交回模型。

完整控制流：

```text
用户问题
  ↓
agent.invoke()
  ↓
Deep Agent 组装系统提示词、用户消息和工具 Schema
  ↓
模型判断是否需要工具
  ↓
模型返回 Tool Call（工具名和参数）
  ↓
Deep Agent 执行 Python 工具
  ↓
工具结果作为 ToolMessage 返回模型
  ↓
模型继续判断或生成最终回答
```

## 3. `create_deep_agent()` 与 `agent.invoke()`

### 3.1 创建阶段

```python
agent = create_deep_agent(
    model=model,
    tools=[internet_search],
    system_prompt=research_instructions,
    middleware=[TodoListMiddleware()],
)
```

这一步组装 Agent：

- `model`：使用哪个模型；
- `tools`：允许执行哪些自定义工具；
- `system_prompt`：Agent 以什么角色和规则工作；
- `middleware`：为运行过程增加哪些辅助能力。

执行到这里时，通常还没有处理具体用户任务。

### 3.2 运行阶段

```python
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "帮我搜索并介绍一下 Deep Agents 的主要用途。",
            }
        ]
    }
)
```

`invoke()` 才会开始一次实际运行：

```text
create_deep_agent() = 配置“这个 Agent 是谁、会什么”
agent.invoke()       = 告诉它“这一次具体做什么”
```

输出中的 `result["messages"]` 包含消息历史，最后一条通常是最终回答：

```python
print(result["messages"][-1].content)
```

## 4. 把 Python 函数变成工具

```python
from typing import Literal
from tavily import TavilyClient

tavily_client = TavilyClient(api_key=tavily_api_key)

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "images"] = "general",
    include_raw_content: bool = True,
):
    """Run a web search for the given query.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        topic: Search category.
        include_raw_content: Whether to include raw page content.
    """
    return tavily_client.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_raw_content=include_raw_content,
    )
```

一个普通 Python 函数要成为易于模型使用的工具，至少需要：

1. 明确的函数名；
2. 清晰的参数名；
3. 类型提示；
4. 合理的默认值；
5. 准确的 docstring；
6. 可序列化的返回结果。

LangChain/Deep Agents 会根据函数签名和 docstring 生成 Tool Schema。模型看到的是工具名称、说明和参数结构，不是 Python 源代码。

### 4.1 `query=query` 怎么理解

```python
return tavily_client.search(query=query)
```

左边的 `query=` 是 Tavily `search()` 的参数名，右边的 `query` 是 `internet_search()` 收到的局部变量。含义是：把外层函数收到的关键词传给 Tavily。

### 4.2 docstring 要与代码一致

如果函数签名是：

```python
include_raw_content: bool = True
```

docstring 就不能写成默认 `False`。真正执行时以函数签名为准，但错误说明会同时误导开发者和模型。

## 5. 系统提示词 `system_prompt`

```python
research_instructions = """你是一位专业的研究员。
你的工作是进行深入研究，然后撰写一份完整的研究报告。

你可以使用 internet_search 工具搜索互联网获取信息。
"""
```

随后传入：

```python
system_prompt=research_instructions
```

它不会训练或永久修改模型，只会在运行时作为当前请求的一部分发送给模型。系统提示词适合定义：

- Agent 的角色；
- 最终任务目标；
- 证据和来源要求；
- 如何处理不确定信息；
- 输出结构和禁止事项。

工具是否真正可执行取决于：

```python
tools=[internet_search]
```

而不是提示词中是否写了“可以使用 internet_search”。提示词用于指导模型何时、为何使用工具；`tools` 才完成实际注册。

## 6. `TodoListMiddleware`

```python
middleware=[TodoListMiddleware()]
```

逐层拆解：

- `TodoListMiddleware`：待办清单中间件类；
- `TodoListMiddleware()`：创建一个中间件实例；
- `[...]`：`middleware` 参数接收中间件列表；
- `middleware=`：把这些中间件安装到 Agent 执行流程。

它为复杂任务提供计划和进度跟踪能力，例如：

```text
1. 搜索 Deep Agents 资料
2. 比较多个来源
3. 整理核心用途
4. 撰写最终报告
```

安装中间件不等于每次必须创建 Todo。简单问题可以直接回答，复杂任务才更有必要拆解。

它与业务工具职责不同：

| 机制 | 职责 |
|---|---|
| `TodoListMiddleware` | 规划和追踪工作步骤 |
| `internet_search` | 真正获取互联网信息 |

参数名是单数 `middleware`，但值是列表。写成 `middlewares=` 会触发 `unexpected keyword argument`。

## 7. 模型、API 协议和 LangChain 适配器

“Deep Agents 支持实现了 Tool Calling 的 LangChain Chat Model”需要分四层理解：

```text
具体模型
  ↓
模型平台和 API
  ↓
LangChain ChatModel 适配器
  ↓
Deep Agent
```

本次实践对应：

```text
deepseek-flash
  ↓
DeepSeek 平台
  ↓
OpenAI-compatible API
  ↓
ChatOpenAI
  ↓
create_deep_agent
```

`ChatOpenAI` 在指定第三方 `base_url` 时，代表使用 OpenAI-compatible 协议的 LangChain 适配器，不表示一定调用 OpenAI 公司的模型。

“接口兼容”也不等于“完整能力兼容”。要用于 Deep Agents，至少需要：

1. 具体模型支持 Tool Calling；
2. 平台 API 接受工具 Schema 并返回结构化调用；
3. LangChain 适配器能够发送和解析相关字段；
4. Deep Agent 能执行工具并把结果送回模型。

普通聊天成功不能证明 Tool Calling 一定成功。

## 8. 环境变量与安全配置

真实密钥只保存在被 Git 忽略的 `.env`：

```env
AGENTSEEK_MODEL=your-model-name
OPENAI_API_KEY=your-model-api-key
OPENAI_API_BASE=https://your-provider.example/v1
TAVILY_API_KEY=your-tavily-key

LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=deepagents-course
```

Python 不会自动读取 `.env`，程序需要显式加载：

```python
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path(__file__).with_name(".env")
load_dotenv(ENV_FILE)
```

然后检查配置：

```python
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise RuntimeError(f"没有读取到 OPENAI_API_KEY，请检查：{ENV_FILE}")
```

注意：

- 环境变量名称必须与代码完全一致；
- 不打印真实密钥；
- 不把 `.env` 提交到 Git；
- 自己的程序不要放进 `.venv` 目录。

## 9. LangSmith 追踪

启用追踪：

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=deepagents-course
```

开启后重新运行程序。本次 Trace 实际观察到：

```text
LangGraph 根运行
├── ChatOpenAI：模型判断需要搜索
├── internet_search：第一次搜索
├── internet_search：第二次搜索
├── ChatOpenAI：根据搜索结果继续判断
├── read_file：读取被卸载到虚拟文件系统的大结果
└── ChatOpenAI：生成最终回答
```

### 9.1 为什么根节点看不到 system prompt

`LangGraph` 根节点记录的是传给 `agent.invoke()` 的外部输入，所以通常只显示用户消息。

系统提示词是在内部模型调用时组装的，应当：

1. 点击 Trace 树中的 `ChatOpenAI` 子节点；
2. 打开该节点的 `Input`；
3. 查找角色为 `System` 的消息；
4. 搜索实际文字“你是一位专业的研究员”，而不是变量名 `research_instructions`。

Python 变量名不会发送给模型，发送的是变量保存的字符串内容。最终系统消息还可能叠加 Deep Agents Harness或中间件说明，因此不一定只包含自己写的三句话。

### 9.2 隐私边界

LangSmith 可能记录：

- 用户输入；
- 系统提示词；
- 模型输入和输出；
- 工具调用参数；
- 工具返回结果；
- 错误和运行元数据。

含敏感信息的任务不应开启云端 Trace，或者必须先脱敏。

## 10. 本章实际遇到的错误

| 报错或现象 | 根因 | 修复 |
|---|---|---|
| `No module named 'deepagents'` | VS Code 使用了没有安装依赖的解释器 | 先核对解释器与项目虚拟环境，不盲目重装 |
| 无法导入 `TodolistMiddleware` | 类名大小写错误 | 改为 `TodoListMiddleware` |
| `Missing credentials` | `.env` 未加载，`api_key=None` | 调用 `load_dotenv()` 并检查变量 |
| API Base 读取不到 | `.env` 与代码使用了不同变量名 | 统一环境变量名称 |
| `unexpected keyword argument 'middlewares'` | 参数名写成复数 | 改为 `middleware=[...]` |
| LangSmith 根节点找不到系统提示词 | 查看的是外层 LangGraph 输入 | 进入 `ChatOpenAI` 子节点查看 Input |
| PowerShell 不认识 `clean` | `clean` 不是 PowerShell 清屏命令 | 使用 `cls` 或 `Clear-Host` |

有效的排错顺序是先看 Traceback 最后一行，再判断层次：

```text
import 报错          → 依赖、解释器或名称问题
模型构造报错        → Key、base_url 或环境变量问题
Agent 创建报错      → create_deep_agent 参数问题
工具运行报错        → 工具实现或外部服务问题
模型未调用工具      → Tool Calling、Schema、提示词或任务性质问题
```

## 11. 学习心得

本章让我从“Agent 就是会调用工具的模型”进一步理解为：

> Agent 是模型决策、工具执行、状态管理和控制循环的组合。模型负责提出下一步，Deep Agent 负责执行和组织运行，工具负责接触外部世界，中间件负责增加通用能力。

LangSmith Trace 把原本不可见的内部过程变成可以检查的调用树，是理解 Tool Calling和排查 Agent行为的重要工具。

目前已经完成：

- 理解 `create_deep_agent()` 与 `agent.invoke()` 的职责；
- 阅读和解释搜索工具的函数签名、docstring 和数据流；
- 理解 `system_prompt`、工具和中间件的责任边界；
- 修复导入、参数和环境变量错误；
- 开启 LangSmith 并观察模型—工具—模型调用链。

仍需通过后续独立练习验证：

- 不参考示例独立编写一个新工具；
- 独立设计更明确的系统提示词；
- 注入工具异常并根据 Trace 独立定位；
- 更换支持 Tool Calling 的模型并解释兼容差异；
- 两天后进行无提示回忆与变体实现。

## 12. 自测题

1. `create_deep_agent()` 和 `agent.invoke()` 分别负责什么？
2. 模型为什么不能直接执行本地 Python 函数？
3. 函数名、类型提示和 docstring 如何影响 Tool Schema？
4. 只在系统提示词写“可以使用搜索工具”，却不注册 `tools`，为什么无法真正搜索？
5. `middleware=[TodoListMiddleware()]` 中括号和方括号分别表示什么？
6. OpenAI-compatible 为什么不等于 Tool Calling一定兼容？
7. LangSmith 根节点和模型子节点的 Input 有什么区别？
8. Trace中没有 Todo调用时，为什么不一定是错误？

## 参考资料

- [Deep Agents 实战 · 第二章 Quickstart](https://datawhalechina.github.io/deepagents-in-action/chapters/ch02-quickstart/)
- [LangChain Chat Model integrations](https://docs.langchain.com/oss/python/integrations/chat)
- [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools)
- [LangSmith：Trace LangChain applications](https://docs.langchain.com/langsmith/trace-with-langchain)
- [LangSmith：Trace Deep Agents applications](https://docs.langchain.com/langsmith/trace-deep-agents)
