"""
AI 媒体生成服务层 — 照片生成视频、老照片修复、照片动画化。

当前状态：模型尚未接入，所有生成函数返回 503 "模型暂未开放"。
链路已完整打通：API → 积分校验 → 服务调用 → 结果返回。
未来接入模型时只需替换 _call_xxx 内部实现即可。
"""
import logging
import uuid
from pathlib import Path

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

# 输出目录
MEDIA_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "static" / "ai_media"


def _ensure_output_dir():
    MEDIA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _check_model_available(api_key: str) -> None:
    """统一检查模型是否可用，不可用时抛 503。"""
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODEL_NOT_AVAILABLE",
                "message": "AI 模型暂未开放，敬请期待",
                "hint": "该功能需要接入 AI 生成模型后才能使用，我们正在努力对接中。",
            },
        )


# ─────────────────────────────────────────────────
# 照片 → 视频（将一张静态照片生成一段短视频）
# ─────────────────────────────────────────────────
async def generate_video_from_photo(image_url: str, style: str = "default") -> dict:
    """
    输入一张已上传照片的 URL，输出一段 AI 生成的短视频。

    流程（模型接入后）：
    1. 下载原图
    2. 调用视频生成 API（如 Runway / Kling / Pika）
    3. 轮询等待结果
    4. 下载视频到本地 static/ai_media/
    5. 返回本地 URL

    当前：返回 503。
    """
    _check_model_available(getattr(settings, "VIDEO_GEN_API_KEY", ""))

    # ---- 以下为模型接入后的预留逻辑 ----
    task_id = uuid.uuid4().hex
    _ensure_output_dir()
    logger.info(f"[generate_video] task={task_id} image={image_url} style={style}")

    # TODO: 调用实际的视频生成 API
    # response = await video_gen_client.generate(image_url, style=style)
    # result_url = f"/static/ai_media/{task_id}.mp4"
    # return {"task_id": task_id, "status": "completed", "result_url": result_url}

    raise HTTPException(status_code=503, detail="不应到达此处")


# ─────────────────────────────────────────────────
# 老照片修复（去噪、上色、增强清晰度）
# ─────────────────────────────────────────────────
async def restore_old_photo(image_url: str, enhance_color: bool = True) -> dict:
    """
    输入一张老照片 URL，输出修复后的高清图片。

    流程（模型接入后）：
    1. 下载原图
    2. 调用图像修复 API（如 GFPGAN / CodeFormer / 阿里图像修复）
    3. 保存修复后图片到 static/ai_media/
    4. 返回本地 URL

    当前：返回 503。
    """
    _check_model_available(getattr(settings, "PHOTO_RESTORE_API_KEY", ""))

    task_id = uuid.uuid4().hex
    _ensure_output_dir()
    logger.info(f"[restore_photo] task={task_id} image={image_url} enhance_color={enhance_color}")

    # TODO: 调用实际的图像修复 API
    raise HTTPException(status_code=503, detail="不应到达此处")


# ─────────────────────────────────────────────────
# 照片动画化（新照片转为动态视频）
# ─────────────────────────────────────────────────
async def animate_photo_to_video(image_url: str, duration_seconds: int = 5) -> dict:
    """
    输入一张照片 URL，输出一段带动画效果的视频（镜头推拉、微动效果等）。

    流程（模型接入后）：
    1. 下载原图
    2. 调用照片动画 API（如 LeiaPix / Immersity AI / 阿里达摩院）
    3. 保存视频到 static/ai_media/
    4. 返回本地 URL

    当前：返回 503。
    """
    _check_model_available(getattr(settings, "VIDEO_GEN_API_KEY", ""))

    task_id = uuid.uuid4().hex
    _ensure_output_dir()
    logger.info(f"[animate_photo] task={task_id} image={image_url} duration={duration_seconds}s")

    # TODO: 调用实际的照片动画 API
    raise HTTPException(status_code=503, detail="不应到达此处")


def get_cost_map() -> dict:
    """返回各功能的积分消耗配置。"""
    from app.services.points import COST_GENERATE_VIDEO, COST_RESTORE_PHOTO, COST_ANIMATE_PHOTO
    return {
        "generate_video": COST_GENERATE_VIDEO,
        "restore_photo": COST_RESTORE_PHOTO,
        "animate_photo": COST_ANIMATE_PHOTO,
    }
