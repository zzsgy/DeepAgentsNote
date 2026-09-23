# 第四章：任务规划研究 Agent

主入口只有一个：[course.py](course.py)。它保留课程的配置、搜索工具、Agent、调用、输出结构。`verify_offline.py` 是可选验证脚本，不是你日常运行研究任务的入口。

完整作业：[第四章学习任务](../../notes/ch04-task-planning.md)。

## 运行环境

- Python 3.12；依赖由 `pyproject.toml` 和 `uv.lock` 固定。
- Deep Agents 0.7.13；需要支持工具调用的 OpenAI-compatible 模型，以及独立的 Tavily API Key。
- 当前验证状态：离线框架行为测试通过；本提交未执行真实联网研究。

在此目录打开终端：

```powershell
uv sync --frozen --python 3.12
uv run --frozen python -X utf8 verify_offline.py
```

离线测试不读取真实 `.env`，阻断 socket 网络，不会消耗模型或 Tavily 额度。第一次 `uv sync` 安装依赖可能需要网络。

## 在 PyCharm 运行课程代码

1. 打开本目录，将解释器选为本目录的 `.venv/Scripts/python.exe`。
2. 复制 `.env.example` 为 `.env`，在本机填写四项配置：

   ```dotenv
   MODEL_NAME=你服务端支持的模型名称
   OPENAI_API_BASE=你的兼容接口地址
   OPENAI_API_KEY=你的模型密钥
   TAVILY_API_KEY=你的Tavily密钥
   ```

3. 直接运行 `course.py`。也可以在终端运行：

   ```powershell
   uv run --frozen python -X utf8 course.py
   ```

这个操作会真实访问你配置的模型服务和 Tavily，可能产生费用。此处只是运行说明，提交作业时没有代你执行。

配置只从 `course.py` 同目录 `.env` 读取，不受 PyCharm Working directory 影响，不回退到其他项目。为确保本地值明确，示例关闭 `.env` 变量插值，应填写完整地址而不是 `${OTHER_VAR}`。

## 查看实际结果

正常返回后查看 `runs/<运行标识>/`：

- `evidence.json`：清单变更、最终 Todo、工具调用与响应配对情况、虚拟文件列表。
- `answer.md`：模型最后一条回复。
- `notes.md`、`final_report.md`：对应虚拟文件存在时才导出。

StateBackend 中的虚拟文件不会自行出现在 Windows 文件夹中，最后的导出代码才执行本机写入。导出仅使用固定文件名，不直接信任模型提供的任意路径。

本示例使用 `invoke` 保持与课程一致，结束后回看记录；若中途抛出异常，就不会导出一份虚假的成功结果。保存控制台错误并排查。需要实时观察时，可把 `invoke` 改为 `stream(..., stream_mode="values")`，作为后续独立练习。

不要仅凭所有 Todo 都是 completed 判定成功。至少核对搜索是否发生、笔记和报告是否存在、报告内容与引用是否可信。工具响应 `success` 也不能排除响应正文含业务错误。

## 与课程相比改了什么

1. 模型和 Tavily 都读取本项目 `.env`，缺配置时提前报错。
2. 保留 `create_deep_agent(..., middleware=[TodoListMiddleware()])`，提取 `build_agent` 方便离线测试。
3. 增加 `main` 入口保护，避免导入模块就运行研究。
4. 提示词补充固定产物路径、来源要求和读回检查。
5. 最后保存真实清单和工具记录，方便提交规划过程证据。

没有默认启用跨调用持久化。离线测试单独配置 `InMemorySaver` 来验证同线程接续与新线程隔离；它不能在进程重启后恢复。

## 常见问题

| 现象 | 优先检查 |
|---|---|
| 配置读取为空 | `.env` 是否位于本目录，四个键是否都有值 |
| IDE 提示可能为 None | 先转字符串并校验；`dotenv_values` 的值允许为空 |
| 导入后突然发请求 | 不要导入其他课程脚本的客户端；确认执行代码有 main 保护 |
| Tavily InvalidAPIKeyError | Tavily 自己的密钥是否有效，不要使用模型密钥代替 |
| 模型接口 400 或工具调用失败 | 模型是否支持当前工具协议和兼容接口 |
| 清单完成但没文件 | 检查工具记录和返回的 `files`；模型的完成声明不是验收 |

`.env`、`.venv`、IDE 设置和 `runs/` 已由仓库忽略规则排除。要发布运行结果，请先人工脱敏，再选择性放入 `evidence/`；不要强制添加整个 runs 目录。
