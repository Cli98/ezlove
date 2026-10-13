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


def get_vision_model() -> str:
    """视觉理解模型：用于海报照片分析等多模态场景。

    文本模型不支持图片输入，必须使用独立配置的多模态模型
    （环境变量 LLM_VISION_MODEL 未配置时回退到实测可用的 qwen3.8-omni-flash）。
    """
    return settings.LLM_VISION_MODEL or "qwen3.8-omni-flash"


def no_thinking_kwargs() -> dict:
    """关闭推理模型思考模式的请求参数。

    qwen3 系默认开启思考模式（reasoning tokens 占大头），对结构化输出/
    工具调用等任务无增益：实测文本 12.1s→3.7s、视觉 20s→6s，且 JSON
    更干净、工具调用兼容。个别不支持该参数的模型由 dashscope 兼容层忽略。
    """
    return {"extra_body": {"enable_thinking": False}}
