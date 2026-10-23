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
    # 视觉理解模型（海报照片分析等）：文本模型不支持图片输入，需独立多模态模型；
    # 留空则用代码默认值（qwen3.8-omni-flash），可在部署配置中覆盖
    LLM_VISION_MODEL: str = ""

    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_ENDPOINT: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_PUBLIC_BASE_URL: str = ""

    # AI 媒体生成（暂未接入）
    VIDEO_GEN_API_KEY: str = ""
    PHOTO_RESTORE_API_KEY: str = ""

    # NB-IoT 硬件事件推送（phchn 云平台）：配置后要求 URL 携带 ?token= 或
    # X-NBIOT-Token 头；留空为不校验（首轮联调）。设备绑定见 config/nbiot_devices.json
    NBIOT_WEBHOOK_SECRET: str = ""
    NBIOT_DEVICES_FILE: str = ""

    # phchn 平台开放 API（社区端设备监控实时状态）：凭证环境变量优先，
    # 缺省读 config/phchn_platform.json（低频静态配置，发布通道不改 .env）
    PHCHN_APP_ID: str = ""
    PHCHN_APP_SECRET: str = ""
    PHCHN_PLATFORM_FILE: str = ""
    PHCHN_API_BASE: str = ""

    # 调度与通知开关（上线 dry-run 时序控制，P3 §3.5；默认值=行为与现状一致）
    SCHEDULER_ENABLED: bool = True
    ALERT_NOTIFY_ENABLED: bool = True
    # >0 时家属侧未读告警仅对 created_at >= now-N小时 的未读牵挂生效（R3 冷启动上限）
    ALERT_COLD_START_UNREAD_HOURS: int = 0
    # >0 时工作台 timed_out 查询仅回看 now-N小时 内产生的告警（R9 冷启动限制）
    WORKSTATION_TIMED_OUT_LOOKBACK_HOURS: int = 0

    class Config:
        env_file = ".env"


settings = Settings()
