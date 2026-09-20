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


async def get_active_relation(db: AsyncSession, family_user_id: UUID, elder_user_id: UUID) -> CareRelation | None:
    """查询指定的 active 家属-老人关系，不存在则返回 None。"""
    # 多行 active 防护（P6 M-1）：双邀请+双绑定可产生同 (family, elder) 对的多行 active 关系，
    # 参与方判定语义（P3 拍板 9 口径）只需存在性，取任一即可，
    # 与下方 exists_active_relation_as_elder 的 limit(1) 范式对齐，避免 scalar_one_or_none 抛 MultipleResultsFound。
    result = await db.execute(
        select(CareRelation).where(
            CareRelation.family_user_id == family_user_id,
            CareRelation.elder_user_id == elder_user_id,
            CareRelation.status == "active",
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def exists_active_relation_as_elder(db: AsyncSession, user_id: UUID) -> bool:
    """判断用户是否为任一 active 关系的老人方（发送角色错向判定，W-02）。"""
    result = await db.execute(
        select(CareRelation.id).where(
            CareRelation.elder_user_id == user_id,
            CareRelation.status == "active",
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None
