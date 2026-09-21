"""LangChain 模型接入：不含密钥；导入本模块不会创建模型或发起请求。"""

import os
from pathlib import Path

# 本示例不上传 Trace；与关闭外部模型调用不是一回事。
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

PROJECT_DIR = Path(__file__).resolve().parent


def build_model(env_file: Path | None = None) -> ChatOpenAI:
    # .env 由运行者填写。已有进程环境变量优先，不覆盖它们。
    load_dotenv(env_file if env_file is not None else PROJECT_DIR / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_API_BASE", "").strip()
    model_name = os.getenv("MODEL_NAME", "deepseek-flash").strip()
    if not api_key:
        raise ValueError("请在 .env 中填写 OPENAI_API_KEY；不要把密钥提交到 Git")
    if not base_url:
        raise ValueError("请在 .env 中填写 OPENAI_API_BASE（不是 OPENAI_API_URL）")
    if not model_name:
        raise ValueError("MODEL_NAME 不能为空")
    return ChatOpenAI(
        model=model_name,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=0,
        timeout=60,
        max_retries=1,
    )
