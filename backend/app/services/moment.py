from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.care_moment import CareMoment
from app.models.view_event import ViewEvent
from app.models.response import Response


async def create_moment(db: AsyncSession, sender_id: UUID, elder_id: UUID, text_content: str | None,
                        media_urls: list | None, is_ai_generated: bool = False,
                        content_type: str | None = None, poster_meta: dict | None = None) -> CareMoment:
    if not content_type:
        content_type = "text"
        if media_urls and text_content:
            content_type = "mixed"
        elif media_urls:
            content_type = "image"

    moment = CareMoment(
        sender_id=sender_id,
        elder_id=elder_id,
        content_type=content_type,
        text_content=text_content,
        media_urls=media_urls,
        is_ai_generated=is_ai_generated,
        poster_meta=poster_meta,
    )
    db.add(moment)
    await db.commit()
    await db.refresh(moment)
    return moment


async def get_moments_for_user(
    db: AsyncSession, user_id: UUID, role: str,
    offset: int = 0, limit: int = 20,
) -> list[CareMoment]:
    if role == "family":
        stmt = (
            select(CareMoment)
            .where(CareMoment.sender_id == user_id)
            .order_by(CareMoment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    else:
        stmt = (
            select(CareMoment)
            .where(CareMoment.elder_id == user_id)
            .order_by(CareMoment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_moments_for_user(db: AsyncSession, user_id: UUID, role: str) -> int:
    if role == "family":
        stmt = select(func.count(CareMoment.id)).where(CareMoment.sender_id == user_id)
    else:
        stmt = select(func.count(CareMoment.id)).where(CareMoment.elder_id == user_id)
    result = await db.execute(stmt)
    return result.scalar() or 0


async def record_view(db: AsyncSession, moment_id: UUID, viewer_id: UUID, duration: int | None = None) -> ViewEvent:
    event = ViewEvent(moment_id=moment_id, viewer_id=viewer_id, view_duration=duration)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def is_moment_read(db: AsyncSession, moment_id: UUID) -> bool:
    result = await db.execute(select(ViewEvent).where(ViewEvent.moment_id == moment_id).limit(1))
    return result.scalar_one_or_none() is not None


async def batch_get_read_moment_ids(db: AsyncSession, moment_ids: list[UUID]) -> set[UUID]:
    """一次查询返回已读的 moment_id 集合，替代逐条调用 is_moment_read。"""
    if not moment_ids:
        return set()
    result = await db.execute(
        select(ViewEvent.moment_id)
        .where(ViewEvent.moment_id.in_(moment_ids))
        .distinct()
    )
    return {row[0] for row in result.all()}


async def create_response(db: AsyncSession, moment_id: UUID, responder_id: UUID,
                          response_type: str, content: str | None = None) -> Response:
    if not content:
        content = response_type
    resp = Response(moment_id=moment_id, responder_id=responder_id, response_type=response_type, content=content)
    db.add(resp)
    await db.commit()
    await db.refresh(resp)
    return resp
