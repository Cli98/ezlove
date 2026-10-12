from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.community import CommunityWorker

security = HTTPBearer()


def get_pagination(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页参数依赖，返回 offset/limit 及原始页码信息"""
    return {
        "offset": (page - 1) * page_size,
        "limit": page_size,
        "page": page,
        "page_size": page_size,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证已过期或无效")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


async def get_current_worker(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CommunityWorker:
    """验证社区工作人员 JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "worker":
            raise HTTPException(status_code=401, detail="无效的社区工作人员凭证")
        worker_id = payload.get("sub")
        if worker_id is None:
            raise HTTPException(status_code=401, detail="无效的 token")
    except JWTError:
        raise HTTPException(status_code=401, detail="认证已过期或无效")

    result = await db.execute(select(CommunityWorker).where(CommunityWorker.id == UUID(worker_id)))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=401, detail="社区工作人员不存在")

    current_community_id = payload.get("current_community_id")
    if current_community_id:
        worker.community_id = UUID(current_community_id)

    return worker
