from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.deps import get_current_user, get_current_worker
from app.models.user import User
from app.models.community import CommunityWorker, CommunityElder
from app.services import volunteer as vol_service
from app.schemas.volunteer import HelpTaskCreate

router = APIRouter(prefix="/volunteer", tags=["volunteer"])


# ── 小程序端（get_current_user） ──

@router.post("/register")
async def register_volunteer(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    elder = (await db.execute(
        select(CommunityElder).where(CommunityElder.elder_id == user.id)
    )).scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=400, detail="未找到老人档案")
    try:
        profile = await vol_service.register_volunteer(db, user.id, elder.id)
        return {"ok": True, "id": str(profile.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-profile")
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await vol_service.get_volunteer_profile(db, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="未注册为志愿者")
    return profile


@router.get("/available-tasks")
async def get_available_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vp = await vol_service.get_volunteer_profile_obj(db, user.id)
    if not vp:
        raise HTTPException(status_code=404, detail="未注册为志愿者")
    return await vol_service.list_tasks(db, vp.community_id, status="pending")


@router.post("/tasks/{task_id}/accept")
async def accept_task(
    task_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await vol_service.accept_task(db, task_id, user.id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class TaskCompleteRequest(BaseModel):
    notes: str | None = None


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: UUID,
    body: TaskCompleteRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        notes = body.notes if body else None
        await vol_service.complete_task(db, task_id, user.id, notes=notes)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-points")
async def get_my_points(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vp = await vol_service.get_volunteer_profile_obj(db, user.id)
    if not vp:
        raise HTTPException(status_code=404, detail="未注册为志愿者")
    return await vol_service.get_points_history(db, user.id)


# ── 管理端（get_current_worker） ──

@router.get("/admin/volunteers")
async def list_volunteers(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    return await vol_service.list_volunteers(db, worker.community_id)


@router.get("/admin/tasks")
async def list_all_tasks(
    status: str | None = None,
    task_type: str | None = None,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    return await vol_service.list_tasks(db, worker.community_id, status=status, task_type=task_type)


@router.post("/admin/tasks")
async def create_task(
    data: HelpTaskCreate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    task = await vol_service.create_task(db, worker.community_id, worker.id, data.model_dump())
    return {"ok": True, "id": str(task.id)}


@router.put("/admin/tasks/{task_id}/verify")
async def verify_task(
    task_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    try:
        await vol_service.verify_task(db, task_id, worker.id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/leaderboard")
async def get_leaderboard(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    return await vol_service.get_leaderboard(db, worker.community_id)
