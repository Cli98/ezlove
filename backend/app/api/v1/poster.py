import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.poster import (
    PosterGenerateRequest, PosterGenerateResponse, PosterVariant,
    PosterRenderRequest, PosterRenderResponse,
)
from app.services.ai_content import analyze_photo_and_suggest
from app.services.poster_generator import generate_all_posters, generate_single_poster, TEMPLATE_REGISTRY

router = APIRouter(prefix="/poster", tags=["poster"])

STATIC_DIR = Path(__file__).resolve().parents[3] / "static"
# 预计算允许的目录真实路径，用于路径遍历校验
_STATIC_REAL = os.path.realpath(str(STATIC_DIR))


def _resolve_image_path(image_url: str) -> str:
    if image_url.startswith("/static/"):
        candidate = str(STATIC_DIR.parent / image_url.lstrip("/"))
    else:
        candidate = str(STATIC_DIR / "uploads" / image_url.split("/")[-1])

    # 使用 realpath 解析符号链接和 ../ 等，确保最终路径在 STATIC_DIR 内
    resolved = os.path.realpath(candidate)
    if not resolved.startswith(_STATIC_REAL + os.sep) and resolved != _STATIC_REAL:
        raise HTTPException(status_code=400, detail="非法的图片路径")
    return resolved


@router.post("/generate", response_model=PosterGenerateResponse)
async def generate_poster(
    req: PosterGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    photo_path = _resolve_image_path(req.image_url)
    if not Path(photo_path).exists():
        raise HTTPException(status_code=400, detail="图片不存在，请重新上传")

    ai_result = await analyze_photo_and_suggest(photo_path, req.user_text)

    captions = ai_result.get("captions", [])
    recommended_template = ai_result.get("recommended_template", "warm_letter")
    photo_description = ai_result.get("photo_description")

    selected_caption = captions[0]["text"] if captions else (req.user_text or "想你了")
    sender_name = user.nickname or "家人"
    date_str = datetime.now().strftime("%Y年%m月%d日")

    poster_results = generate_all_posters(photo_path, selected_caption, date_str, sender_name)

    variants = []
    recommended_index = 0
    for i, pr in enumerate(poster_results):
        variants.append(PosterVariant(
            template_name=pr["template_name"],
            poster_url=pr["poster_url"],
            caption=selected_caption,
            label=pr["label"],
            desc=pr["desc"],
        ))
        if pr["template_name"] == recommended_template:
            recommended_index = i

    return PosterGenerateResponse(
        variants=variants,
        recommended_index=recommended_index,
        photo_description=photo_description,
    )


@router.post("/render-single", response_model=PosterRenderResponse)
async def render_single(
    req: PosterRenderRequest,
    user: User = Depends(get_current_user),
):
    photo_path = _resolve_image_path(req.image_url)
    if not Path(photo_path).exists():
        raise HTTPException(status_code=400, detail="图片不存在，请重新上传")

    if req.template_name not in TEMPLATE_REGISTRY:
        raise HTTPException(status_code=400, detail="未知模板")

    sender_name = req.sender_name or user.nickname or "家人"
    date_str = datetime.now().strftime("%Y年%m月%d日")

    poster_url = generate_single_poster(req.template_name, photo_path, req.caption, date_str, sender_name)
    return PosterRenderResponse(poster_url=poster_url)
