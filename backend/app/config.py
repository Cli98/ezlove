from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "EZLove"
    DEBUG: bool = False

    DATABASE_URL: str = ""
    REDIS_URL: str = ""

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174"]

    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    WECHAT_UNREAD_TEMPLATE_ID: str = ""
    WECHAT_ALERT_TEMPLATE_ID: str = ""

    ANTHROPIC_API_KEY: str = ""

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "qwen-plus"

    # AI 媒体生成（暂未接入）
    VIDEO_GEN_API_KEY: str = ""
    PHOTO_RESTORE_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
