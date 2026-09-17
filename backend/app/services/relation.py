import random
import string
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.care_relation import CareRelation


def _generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def create_invite(db: AsyncSession, family_user_id: UUID) -> CareRelation:
    code = _generate_code()
    relation = CareRelation(family_user_id=family_user_id, invite_code=code, status="pending")
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return relation


async def bind_by_code(db: AsyncSession, elder_user_id: UUID, invite_code: str) -> CareRelation:
    result = await db.execute(
        select(CareRelation).where(CareRelation.invite_code == invite_code, CareRelation.status == "pending")
    )
    relation = result.scalar_one_or_none()
    if relation is None:
        raise ValueError("邀请码无效或已被使用")
    relation.elder_user_id = elder_user_id
    relation.status = "active"
    await db.commit()
    await db.refresh(relation)
    return relation


async def get_relations(db: AsyncSession, user_id: UUID) -> list[CareRelation]:
    result = await db.execute(
        select(CareRelation).where(
            ((CareRelation.family_user_id == user_id) | (CareRelation.elder_user_id == user_id)),
            CareRelation.status == "active",
        )
    )
    return list(result.scalars().all())
