"""第三章实验：只有测试模型是替身，Agent、工具、Backend 均使用真实框架。"""

import os

# 不读取 .env，不向外部 tracing 服务上传实验。必须在导入 LangChain 前设置。
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
