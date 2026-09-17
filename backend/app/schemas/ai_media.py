"""AI 媒体生成相关 Schema。"""
from uuid import UUID
from pydantic import BaseModel, Field


# ── 请求 ──────────────────────────────────────────

class GenerateVideoRequest(BaseModel):
    """照片生成视频请求。"""
    image_url: str = Field(..., description="已上传的图片 URL")
    style: str | None = Field(default="default", description="视频风格：default/warm/cinematic")


class RestorePhotoRequest(BaseModel):
    """老照片修复请求。"""
    image_url: str = Field(..., description="已上传的老照片 URL")
    enhance_color: bool = Field(default=True, description="是否同时增强色彩")


class AnimatePhotoRequest(BaseModel):
    """照片动画化请求（新照片转为短视频）。"""
    image_url: str = Field(..., description="已上传的照片 URL")
    duration_seconds: int = Field(default=5, ge=3, le=15, description="生成视频时长（秒）")


# ── 响应 ──────────────────────────────────────────

class AiMediaTaskResponse(BaseModel):
    """AI 媒体生成任务响应（同步返回或异步轮询）。"""
    task_id: str
    status: str                         # "processing" | "completed" | "failed"
    result_url: str | None = None       # 生成后的媒体 URL
    points_deducted: int = 0
    message: str | None = None


class AiMediaCostInfo(BaseModel):
    """各 AI 功能的积分消耗一览。"""
    generate_video: int
    restore_photo: int
    animate_photo: int
