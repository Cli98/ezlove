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
    # 设备关怀阈值（2026-10-28 与白莉娜老师确认）：
    # 红外 1 小时无活动、红外 12 小时无生活轨迹、门磁 24 小时未触发
    ("A", "stillness", 1),
    ("B", "stillness", 1),
    ("C", "stillness", 1),
    ("A", "no_activity_trace", 12),
    ("B", "no_activity_trace", 12),
    ("C", "no_activity_trace", 12),
    ("A", "no_outing", 24),
    ("B", "no_outing", 24),
    ("C", "no_outing", 24),
]

# 设备关怀规则的可调参数默认值（存在 alert_rules.config 里，社区可自行改）
# check_hours：生效时段 [起, 止)，夜间睡眠不判静止；check_hour：每日检查时点
RULE_DEFAULTS = {
    "stillness": {"check_hours": [7, 22], "dedupe_hours": 6},
    "no_activity_trace": {"check_hours": [0, 24], "dedupe_hours": 12},
    "no_outing": {"check_hour": 8, "dedupe_hours": 24},
}


async def seed_default_rules(db: AsyncSession, community_id: UUID) -> list[AlertRule]:
    """补齐缺失的默认规则：已有的规则保留社区自定义值，不覆盖。"""
    existing = {
        (rule.care_level, rule.rule_type)
        for rule in (await db.execute(
            select(AlertRule).where(AlertRule.community_id == community_id)
        )).scalars()
    }

    rules = []
    for care_level, rule_type, threshold in DEFAULTS:
        if (care_level, rule_type) in existing:
            continue
        rule = AlertRule(
            community_id=community_id,
            care_level=care_level,
            rule_type=rule_type,
            threshold_hours=threshold,
            config=dict(RULE_DEFAULTS.get(rule_type) or {}) or None,
        )
        db.add(rule)
        rules.append(rule)
    await db.flush()
    return rules


async def load_rule_config(
    db: AsyncSession, community_id: UUID, rule_type: str
) -> dict[str, dict]:
    """按护理等级取规则配置：数据库优先，缺失回退内置默认。

    返回 {care_level: {"hours": int, "enabled": bool, "params": dict}}，
    params 为 RULE_DEFAULTS 与 alert_rules.config 合并后的可调参数。
    """
    base_params = RULE_DEFAULTS.get(rule_type) or {}
    config = {
        care_level: {
            "hours": threshold,
            "enabled": True,
            "params": dict(base_params),
        }
        for care_level, rt, threshold in DEFAULTS
        if rt == rule_type
    }

    rows = (await db.execute(
        select(AlertRule).where(
            AlertRule.community_id == community_id,
            AlertRule.rule_type == rule_type,
        )
    )).scalars().all()
    for rule in rows:
        params = dict(base_params)
        params.update(rule.config or {})
        config[rule.care_level] = {
            "hours": rule.threshold_hours,
            "enabled": bool(rule.enabled),
            "params": params,
        }
    return config


async def list_rules(db: AsyncSession, community_id: UUID) -> list[AlertRule]:
    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.community_id == community_id)
        .order_by(AlertRule.care_level, AlertRule.rule_type)
    )
    return list(result.scalars().all())


async def update_rule(db: AsyncSession, community_id: UUID, rule_id: UUID, updates: dict) -> AlertRule:
    # 按社区隔离：id + community_id 双条件，跨社区与不存在统一 404（W-08，防探测）
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.community_id == community_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise ValueError("规则不存在")

    for key, value in updates.items():
        if hasattr(rule, key):
            setattr(rule, key, value)
    await db.flush()
    return rule
