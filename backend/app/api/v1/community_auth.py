from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from passlib.context import CryptContext
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.deps import get_current_worker
from app.models.community import CommunityWorker, Community
from app.models.community_worker_assignment import CommunityWorkerAssignment
from app.services.auth import create_access_token, create_refresh_token

router = APIRouter(prefix="/community/auth", tags=["community-auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"])


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    worker: dict


@router.post("/login", response_model=TokenResponse)
async def community_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(CommunityWorker).where(CommunityWorker.phone == data.phone)
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()

    if not worker or not pwd_ctx.verify(data.password, worker.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")

    token_data = {
        "type": "worker",
        "community_id": str(worker.community_id),
        "current_community_id": str(worker.community_id),
    }
    access_token = create_access_token(worker.id, extra_claims=token_data)
    refresh_token = create_refresh_token(worker.id, extra_claims=token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        worker={
            "id": str(worker.id),
            "name": worker.name,
            "phone": worker.phone,
            "role_label": worker.role_label,
            "community_id": str(worker.community_id),
        },
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def community_refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(data.refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="刷新令牌无效")
        worker_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="刷新令牌无效")

    result = await db.execute(select(CommunityWorker).where(CommunityWorker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=401, detail="社区工作人员不存在")

    token_data = {
        "type": "worker",
        "community_id": str(worker.community_id),
        "current_community_id": str(worker.community_id),
    }
    access_token = create_access_token(worker.id, extra_claims=token_data)
    refresh_token = create_refresh_token(worker.id, extra_claims=token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        worker={
            "id": str(worker.id),
            "name": worker.name,
            "phone": worker.phone,
            "role_label": worker.role_label,
            "community_id": str(worker.community_id),
        },
    )


@router.get("/communities")
async def list_worker_communities(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """Return list of communities this worker can access."""
    stmt = (
        select(CommunityWorkerAssignment, Community)
        .join(Community, CommunityWorkerAssignment.community_id == Community.id)
        .where(CommunityWorkerAssignment.worker_id == worker.id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Always include the worker's default community
    communities = []
    default_included = False
    for assignment, community in rows:
        entry = {
            "community_id": str(community.id),
            "community_name": community.name,
            "role_label": assignment.role_label,
        }
        if community.id == worker.community_id:
            default_included = True
        communities.append(entry)

    if not default_included:
        default_stmt = select(Community).where(Community.id == worker.community_id)
        default_result = await db.execute(default_stmt)
        default_community = default_result.scalar_one_or_none()
        if default_community:
            communities.insert(0, {
                "community_id": str(default_community.id),
                "community_name": default_community.name,
                "role_label": worker.role_label,
            })

    return communities


class SwitchCommunityRequest(BaseModel):
    community_id: UUID


@router.post("/switch-community")
async def switch_community(
    data: SwitchCommunityRequest,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """Switch the worker's current community context. Issues new tokens."""
    # Verify the worker has access to this community via assignments
    # or it is their default community
    is_default = worker.community_id == data.community_id

    if not is_default:
        stmt = select(CommunityWorkerAssignment).where(
            CommunityWorkerAssignment.worker_id == worker.id,
            CommunityWorkerAssignment.community_id == data.community_id,
        )
        result = await db.execute(stmt)
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise HTTPException(status_code=403, detail="无权访问该社区")

    token_data = {
        "type": "worker",
        "community_id": str(data.community_id),
        "current_community_id": str(data.community_id),
    }
    access_token = create_access_token(worker.id, extra_claims=token_data)
    refresh_token = create_refresh_token(worker.id, extra_claims=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "community_id": str(data.community_id),
    }
