import logging
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
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _client


def get_model() -> str:
    return settings.LLM_MODEL or "qwen-plus"
