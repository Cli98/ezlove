import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.volunteer import VolunteerProfile, HelpTask, PointTransaction
from app.models.community import CommunityElder
from app.models.user import User


async def register_volunteer(
    db: AsyncSession,
    user_id: uuid.UUID,
    community_elder_id: uuid.UUID,
) -> VolunteerProfile:
    elder = await db.get(CommunityElder, community_elder_id)
    if not elder:
        raise ValueError("老人档案不存在")
    if elder.care_level != "C":
        raise ValueError("仅 C 级老人可注册为志愿者")

    existing = (await db.execute(
        select(VolunteerProfile).where(VolunteerProfile.user_id == user_id)
    )).scalar_one_or_none()
    if existing:
        raise ValueError("已注册为志愿者")

    profile = VolunteerProfile(
        elder_id=community_elder_id,
        user_id=user_id,
        community_id=elder.community_id,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_volunteer_profile_obj(db: AsyncSession, user_id: uuid.UUID) -> VolunteerProfile | None:
    result = await db.execute(
        select(VolunteerProfile).where(VolunteerProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_volunteer_profile(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(VolunteerProfile, User.nickname)
        .join(User, VolunteerProfile.user_id == User.id)
        .where(VolunteerProfile.user_id == user_id)
    )
    row = result.one_or_none()
    if not row:
        return None
    profile, nickname = row
    return {
        "id": str(profile.id),
        "elder_id": str(profile.elder_id),
        "user_id": str(profile.user_id),
        "total_points": profile.total_points,
        "available_points": profile.available_points,
        "is_active": profile.is_active,
        "created_at": profile.created_at.isoformat(),
        "elder_name": nickname,
    }


async def create_task(
    db: AsyncSession,
    community_id: uuid.UUID,
    worker_id: uuid.UUID,
    data: dict,
) -> HelpTask:
    task = HelpTask(
        community_id=community_id,
        assigned_by=worker_id,
        **data,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(
    db: AsyncSession,
    community_id: uuid.UUID,
    status: str | None = None,
    task_type: str | None = None,
) -> list[dict]:
    stmt = select(HelpTask).where(HelpTask.community_id == community_id)
    if status:
        stmt = stmt.where(HelpTask.status == status)
    if task_type:
        stmt = stmt.where(HelpTask.task_type == task_type)
    stmt = stmt.order_by(HelpTask.created_at.desc())
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    vol_ids = {t.volunteer_id for t in tasks if t.volunteer_id}
    elder_ids = {t.target_elder_id for t in tasks if t.target_elder_id}

    vol_names = {}
    if vol_ids:
        r = await db.execute(
            select(VolunteerProfile.id, User.nickname)
            .join(User, VolunteerProfile.user_id == User.id)
            .where(VolunteerProfile.id.in_(vol_ids))
        )
        vol_names = {vid: name for vid, name in r.all()}

    elder_names = {}
    if elder_ids:
        r = await db.execute(
            select(CommunityElder.id, User.nickname)
            .join(User, CommunityElder.elder_id == User.id)
            .where(CommunityElder.id.in_(elder_ids))
        )
        elder_names = {eid: name for eid, name in r.all()}

    return [
        {
            "id": str(t.id),
            "title": t.title,
            "task_type": t.task_type,
            "target_elder_id": str(t.target_elder_id) if t.target_elder_id else None,
            "point_value": t.point_value,
            "volunteer_id": str(t.volunteer_id) if t.volunteer_id else None,
            "status": t.status,
            "notes": t.notes,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "verified_at": t.verified_at.isoformat() if t.verified_at else None,
            "created_at": t.created_at.isoformat(),
            "volunteer_name": vol_names.get(t.volunteer_id),
            "target_elder_name": elder_names.get(t.target_elder_id),
        }
        for t in tasks
    ]


async def accept_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
) -> HelpTask:
    profile = (await db.execute(
        select(VolunteerProfile).where(VolunteerProfile.user_id == user_id)
    )).scalar_one_or_none()
    if not profile:
        raise ValueError("未注册为志愿者")

    task = await db.get(HelpTask, task_id)
    if not task:
        raise ValueError("任务不存在")
    if task.status != "pending":
        raise ValueError("任务不可接取")

    task.volunteer_id = profile.id
    task.status = "accepted"
    await db.commit()
    await db.refresh(task)
    return task


async def complete_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    notes: str | None = None,
) -> HelpTask:
    profile = (await db.execute(
        select(VolunteerProfile).where(VolunteerProfile.user_id == user_id)
    )).scalar_one_or_none()
    if not profile:
        raise ValueError("未注册为志愿者")

    task = await db.get(HelpTask, task_id)
    if not task:
        raise ValueError("任务不存在")
    if task.volunteer_id != profile.id:
        raise ValueError("非该任务志愿者")
    if task.status != "accepted":
        raise ValueError("任务状态不正确")

    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    if notes:
        task.notes = notes
    await db.commit()
    await db.refresh(task)
    return task


async def verify_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    worker_id: uuid.UUID,
) -> HelpTask:
    task = await db.get(HelpTask, task_id)
    if not task:
        raise ValueError("任务不存在")
    if task.status != "completed":
        raise ValueError("任务尚未完成")

    task.status = "verified"
    task.verified_by = worker_id
    task.verified_at = datetime.now(timezone.utc)
    await db.commit()

    profile = await db.get(VolunteerProfile, task.volunteer_id)
    profile.total_points += task.point_value
    profile.available_points += task.point_value

    txn = PointTransaction(
        volunteer_id=profile.id,
        transaction_type="earn",
        amount=task.point_value,
        balance_after=profile.available_points,
        reference_type="task",
        reference_id=task.id,
        description=f"完成任务：{task.title}",
    )
    db.add(txn)
    await db.commit()
    await db.refresh(task)
    return task


async def get_points_history(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict]:
    profile = (await db.execute(
        select(VolunteerProfile).where(VolunteerProfile.user_id == user_id)
    )).scalar_one_or_none()
    if not profile:
        return []

    result = await db.execute(
        select(PointTransaction)
        .where(PointTransaction.volunteer_id == profile.id)
        .order_by(PointTransaction.created_at.desc())
        .limit(50)
    )
    return [
        {
            "id": str(t.id),
            "transaction_type": t.transaction_type,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "reference_type": t.reference_type,
            "description": t.description,
            "created_at": t.created_at.isoformat(),
        }
        for t in result.scalars().all()
    ]


async def get_leaderboard(
    db: AsyncSession,
    community_id: uuid.UUID,
    limit: int = 20,
) -> list[dict]:
    result = await db.execute(
        select(
            VolunteerProfile.id,
            User.nickname,
            VolunteerProfile.total_points,
        )
        .join(User, VolunteerProfile.user_id == User.id)
        .where(VolunteerProfile.community_id == community_id, VolunteerProfile.is_active.is_(True))
        .order_by(VolunteerProfile.total_points.desc())
        .limit(limit)
    )
    rows = result.all()

    vol_ids = [r[0] for r in rows]
    task_counts = {}
    if vol_ids:
        tc_result = await db.execute(
            select(HelpTask.volunteer_id, func.count(HelpTask.id))
            .where(HelpTask.volunteer_id.in_(vol_ids), HelpTask.status == "verified")
            .group_by(HelpTask.volunteer_id)
        )
        task_counts = {vid: cnt for vid, cnt in tc_result.all()}

    return [
        {
            "volunteer_id": str(vid),
            "elder_name": name,
            "total_points": pts,
            "task_count": task_counts.get(vid, 0),
        }
        for vid, name, pts in rows
    ]


async def list_volunteers(
    db: AsyncSession,
    community_id: uuid.UUID,
) -> list[dict]:
    result = await db.execute(
        select(VolunteerProfile, User.nickname)
        .join(User, VolunteerProfile.user_id == User.id)
        .where(VolunteerProfile.community_id == community_id)
        .order_by(VolunteerProfile.total_points.desc())
    )
    return [
        {
            "id": str(p.id),
            "user_id": str(p.user_id),
            "elder_name": name,
            "total_points": p.total_points,
            "available_points": p.available_points,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat(),
        }
        for p, name in result.all()
    ]
