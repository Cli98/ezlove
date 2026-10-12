import logging

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.schemas.auth import WxLoginRequest, DevLoginRequest, RefreshRequest, TokenResponse
from app.services import points as points_service
from app.services.auth import get_or_create_user, create_access_token, create_refresh_token
from app.utils.wechat import code_to_openid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_daily_bonus(db: AsyncSession, user_id: UUID) -> None:
    """每日首次登录发放积分奖励；发放失败不影响登录主流程。"""
    try:
        await points_service.check_daily_bonus(db, user_id)
    except Exception:
        logger.exception("每日登录奖励发放失败 user_id=%s", user_id)


@router.post("/wx-login", response_model=TokenResponse)
async def wx_login(req: WxLoginRequest, db: AsyncSession = Depends(get_db)):
    openid = await code_to_openid(req.code)
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录失败")
    user = await get_or_create_user(db, openid)
    await _issue_daily_bonus(db, user.id)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user={"id": str(user.id), "nickname": user.nickname, "role": user.role},
    )


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(req: DevLoginRequest = None, db: AsyncSession = Depends(get_db)):
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="仅开发环境可用")
    openid = req.openid if req else "dev_test_user"
    user = await get_or_create_user(db, openid)
    await _issue_daily_bonus(db, user.id)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user={"id": str(user.id), "nickname": user.nickname, "role": user.role},
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(req.refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="刷新令牌无效")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="刷新令牌无效")

    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user={"id": str(user.id), "nickname": user.nickname, "role": user.role},
    )
