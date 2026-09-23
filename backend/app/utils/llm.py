import logging
import httpx2
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger("ezlove.llm")

_client = None


def get_client() -> AsyncOpenAI | None:
    global _client
    api_key = settings.LLM_API_KEY or settings.ANTHROPIC_API_KEY
    base_url = settings.LLM_BASE_URL or None
    if not api_key:
        return None
    if _client is None:
        # 线上容器出网环境特殊：默认地址族选择会先尝试 IPv6 而长时间挂起
        # （实测 openai.APITimeoutError: Request timed out，底层 ConnectTimeout）。
        # 注入 httpx2（openai 3.x 的底层 HTTP 客户端，实测同源可注入）并强制 IPv4 出站
        # （与主机 curl -4 行为一致），同时放宽连接超时以容忍容器内 DNS 缓慢。
        timeout = httpx2.Timeout(120.0, connect=30.0)
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            http_client=httpx2.AsyncClient(
                transport=httpx2.AsyncHTTPTransport(local_address="0.0.0.0"),
                timeout=timeout,
            ),
        )
    return _client


def get_model() -> str:
    return settings.LLM_MODEL or "qwen-plus"
