from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.care_moment import CareMoment
from app.models.view_event import ViewEvent
from app.models.response import Response
from app.services.relation import get_active_relation, exists_active_relation_as_elder


async def create_moment(db: AsyncSession, sender_id: UUID, elder_id: UUID, text_content: str | None,
                        media_urls: list | None, is_ai_generated: bool = False,
                        content_type: str | None = None, poster_meta: dict | None = None) -> CareMoment:
    # 发送为家属专属：无 active 关系时区分角色错向（W-02）与未绑定（W-01）
    relation = await get_active_relation(db, sender_id, elder_id)
    if relation is None:
        if await exists_active_relation_as_elder(db, sender_id):
            raise PermissionError("仅家人可发送牵挂")
        raise PermissionError("请先与老人完成绑定，再发送牵挂")

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


async def record_view(db: AsyncSession, moment_id: UUID, viewer_id: UUID, duration: int | None = None) -> ViewEvent | None:
    """记录查看行为。

    判定顺序：先存在性（404，防探测）后关系（403）。
    查看为双角色，但仅 moment 参与方（sender/elder）可查看（W-03）；
    且只有老人本人的查看才写入 view_events——家属回看自己发的内容
    不产生"已读"信号（OP-4），此时返回 None。
    """
    result = await db.execute(select(CareMoment).where(CareMoment.id == moment_id))
    moment = result.scalar_one_or_none()
    if moment is None:
        raise ValueError("内容不存在")
    if viewer_id not in (moment.sender_id, moment.elder_id):
        raise PermissionError("无权操作")
    if viewer_id != moment.elder_id:
        # 发送者（家属）查看，不计入已读
        return None
    event = ViewEvent(moment_id=moment_id, viewer_id=viewer_id, view_duration=duration)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def is_moment_read(db: AsyncSession, moment_id: UUID, elder_id: UUID) -> bool:
    """已读判定只统计老人本人（viewer == elder）的查看记录（OP-9）。"""
    result = await db.execute(
        select(ViewEvent.id).where(
            ViewEvent.moment_id == moment_id,
            ViewEvent.viewer_id == elder_id,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def batch_get_read_moment_ids(db: AsyncSession, moment_ids: list[UUID]) -> set[UUID]:
    """一次查询返回已读的 moment_id 集合，只统计老人本人（viewer == elder）的查看记录（OP-9）。"""
    if not moment_ids:
        return set()
    result = await db.execute(
        select(ViewEvent.moment_id)
        .join(CareMoment, ViewEvent.moment_id == CareMoment.id)
        .where(
            ViewEvent.moment_id.in_(moment_ids),
            ViewEvent.viewer_id == CareMoment.elder_id,
        )
        .distinct()
    )
    return {row[0] for row in result.all()}


async def create_response(db: AsyncSession, moment_id: UUID, responder_id: UUID,
                          response_type: str, content: str | None = None) -> Response:
    """老人对牵挂内容回应（点赞/语音等）。判定顺序：先存在性（404）后关系（403）。

    回应为老人专属：仅该 moment 的 elder 本人可回应（W-04，
    家属/第三方统一匿名化文案，防关系信息泄露）。
    """
    result = await db.execute(select(CareMoment).where(CareMoment.id == moment_id))
    moment = result.scalar_one_or_none()
    if moment is None:
        raise ValueError("内容不存在")
    if responder_id != moment.elder_id:
        raise PermissionError("无权操作")
    if not content:
        content = response_type
    resp = Response(moment_id=moment_id, responder_id=responder_id, response_type=response_type, content=content)
    db.add(resp)
    await db.commit()
    await db.refresh(resp)
    return resp
