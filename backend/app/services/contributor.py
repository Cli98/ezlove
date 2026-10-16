from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contributor import Contributor


async def list_active_contributors(db: AsyncSession) -> list[Contributor]:
    """贡献页名单：仅返回启用中记录，按排序值升序"""
    result = await db.execute(
        select(Contributor)
        .where(Contributor.is_active.is_(True))
        .order_by(Contributor.sort_order, Contributor.created_at)
    )
    return list(result.scalars().all())
