import uuid
from datetime import datetime, timezone, date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community, CommunityWorker, CommunityElder
from app.models.user import User
from app.models.view_event import ViewEvent


async def create_elder_record(
    db: AsyncSession,
    community_id: uuid.UUID,
    data: dict,
) -> CommunityElder:
    elder = CommunityElder(community_id=community_id, **data)
    db.add(elder)
    await db.commit()
    await db.refresh(elder)
    return elder


async def update_elder_record(
    db: AsyncSession,
    elder_record_id: uuid.UUID,
    updates: dict,
) -> CommunityElder:
    stmt = select(CommunityElder).where(CommunityElder.id == elder_record_id)
    result = await db.execute(stmt)
    elder = result.scalar_one_or_none()
    if not elder:
        raise ValueError("老人档案不存在")
    for key, value in updates.items():
        setattr(elder, key, value)
    await db.commit()
    await db.refresh(elder)
    return elder


async def list_elders(
    db: AsyncSession,
    community_id: uuid.UUID,
    care_level: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[dict]:
    stmt = (
        select(CommunityElder, User.nickname, User.phone)
        .join(User, CommunityElder.elder_id == User.id)
        .where(CommunityElder.community_id == community_id)
    )
    if care_level:
        stmt = stmt.where(CommunityElder.care_level == care_level)
    if search:
        stmt = stmt.where(User.nickname.ilike(f"%{search}%"))
    stmt = stmt.order_by(CommunityElder.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    today_start = datetime.combine(date.today(), datetime.min.time())
    elder_ids = [row[0].elder_id for row in rows]
    active_stmt = (
        select(ViewEvent.viewer_id)
        .where(ViewEvent.viewer_id.in_(elder_ids))
        .where(ViewEvent.viewed_at >= today_start)
        .distinct()
    )
    active_result = await db.execute(active_stmt)
    active_ids = set(active_result.scalars().all())

    return [
        {
            **row[0].__dict__,
            "elder_name": row[1],
            "elder_phone": row[2],
            "today_active": row[0].elder_id in active_ids,
        }
        for row in rows
    ]


async def count_elders(
    db: AsyncSession,
    community_id: uuid.UUID,
    care_level: str | None = None,
    search: str | None = None,
) -> int:
    stmt = (
        select(func.count(CommunityElder.id))
        .join(User, CommunityElder.elder_id == User.id)
        .where(CommunityElder.community_id == community_id)
    )
    if care_level:
        stmt = stmt.where(CommunityElder.care_level == care_level)
    if search:
        stmt = stmt.where(User.nickname.ilike(f"%{search}%"))
    result = await db.execute(stmt)
    return result.scalar() or 0


async def get_elder_detail(
    db: AsyncSession,
    elder_record_id: uuid.UUID,
    community_id: uuid.UUID,
) -> dict | None:
    stmt = (
        select(CommunityElder, User.nickname, User.phone)
        .join(User, CommunityElder.elder_id == User.id)
        .where(
            CommunityElder.id == elder_record_id,
            CommunityElder.community_id == community_id,
        )
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if not row:
        return None
    return {**row[0].__dict__, "elder_name": row[1], "elder_phone": row[2]}
