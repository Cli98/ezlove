"""AI 媒体生成 API 路由 — 照片生成视频、老照片修复、照片动画化。

所有端点均需登录，调用前会校验积分余额，不足时返回 402。
模型未接入时返回 503 MODEL_NOT_AVAILABLE。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.services import ai_media, points as points_service
from app.schemas.ai_media import (
    GenerateVideoRequest,
    RestorePhotoRequest,
    AnimatePhotoRequest,
    AiMediaTaskResponse,
    AiMediaCostInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/media", tags=["ai-media"])


@router.get("/cost", response_model=AiMediaCostInfo)
async def get_ai_media_cost():
    """查询各 AI 媒体功能的积分消耗。"""
    cost = ai_media.get_cost_map()
    return AiMediaCostInfo(**cost)


@router.post("/generate-video", response_model=AiMediaTaskResponse)
async def generate_video(
    req: GenerateVideoRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """使用照片生成 AI 视频，消耗积分。"""
    cost = point_service.COST_GENERATE_VIDEO

    # 积分预扣
    try:
        await points_service.spend_points(db, user.id, cost, "ai_video", "AI 照片生成视频")
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))

    # 调用生成服务（可能 503）
    try:
        result = await ai_media.generate_video_from_photo(req.image_url, style=req.style or "default")
        return AiMediaTaskResponse(
            task_id=result["task_id"],
            status=result["status"],
            result_url=result.get("result_url"),
            points_deducted=cost,
        )
    except HTTPException:
        # 生成失败 → 退还积分
        await points_service.earn_points(db, user.id, cost, "ai_video_refund", "AI 视频生成失败，积分退还")
        raise


@router.post("/restore-photo", response_model=AiMediaTaskResponse)
async def restore_photo(
    req: RestorePhotoRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 老照片修复，消耗积分。"""
    cost = points_service.COST_RESTORE_PHOTO

    try:
        await points_service.spend_points(db, user.id, cost, "ai_restore", "AI 老照片修复")
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))

    try:
        result = await ai_media.restore_old_photo(req.image_url, enhance_color=req.enhance_color)
        return AiMediaTaskResponse(
            task_id=result["task_id"],
            status=result["status"],
            result_url=result.get("result_url"),
            points_deducted=cost,
        )
    except HTTPException:
        await points_service.earn_points(db, user.id, cost, "ai_restore_refund", "AI 修复失败，积分退还")
        raise


@router.post("/animate-photo", response_model=AiMediaTaskResponse)
async def animate_photo(
    req: AnimatePhotoRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """照片动画化（新照片转视频），消耗积分。"""
    cost = points_service.COST_ANIMATE_PHOTO

    try:
        await points_service.spend_points(db, user.id, cost, "ai_animate", "AI 照片动画化")
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))

    try:
        result = await ai_media.animate_photo_to_video(req.image_url, duration_seconds=req.duration_seconds)
        return AiMediaTaskResponse(
            task_id=result["task_id"],
            status=result["status"],
            result_url=result.get("result_url"),
            points_deducted=cost,
        )
    except HTTPException:
        await points_service.earn_points(db, user.id, cost, "ai_animate_refund", "AI 动画失败，积分退还")
        raise
