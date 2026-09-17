from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_rule import AlertRule

DEFAULTS = [
    # (care_level, rule_type, threshold_hours)
    ("A", "unread_timeout", 6),
    ("A", "canteen_absence", 6),   # 1 餐 ≈ 6 小时
    ("A", "no_signal", 12),
    ("B", "unread_timeout", 12),
    ("B", "canteen_absence", 12),  # 2 餐 ≈ 12 小时
    ("B", "no_signal", 24),
    ("C", "unread_timeout", 24),
    ("C", "canteen_absence", 18),  # 3 餐 ≈ 18 小时
    ("C", "no_signal", 48),
]


async def seed_default_rules(db: AsyncSession, community_id: UUID) -> list[AlertRule]:
    existing = await db.execute(
        select(AlertRule).where(AlertRule.community_id == community_id)
    )
    if existing.scalars().first():
        return []

    rules = []
    for care_level, rule_type, threshold in DEFAULTS:
        rule = AlertRule(
            community_id=community_id,
            care_level=care_level,
            rule_type=rule_type,
            threshold_hours=threshold,
        )
        db.add(rule)
        rules.append(rule)
    await db.flush()
    return rules


async def list_rules(db: AsyncSession, community_id: UUID) -> list[AlertRule]:
    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.community_id == community_id)
        .order_by(AlertRule.care_level, AlertRule.rule_type)
    )
    return list(result.scalars().all())


async def update_rule(db: AsyncSession, rule_id: UUID, updates: dict) -> AlertRule:
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise ValueError("规则不存在")

    for key, value in updates.items():
        if hasattr(rule, key):
            setattr(rule, key, value)
    await db.flush()
    return rule
