"""用户积分服务 — 积分账户管理、收入/支出/查询。"""
import logging
from uuid import UUID
from datetime import datetime, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_points import UserPointAccount, UserPointTransaction

logger = logging.getLogger(__name__)

# ── 积分规则 ──────────────────────────────────────
EARN_SEND_MOMENT = 5      # 发送一条牵挂
EARN_VIEW_MOMENT = 2      # 查看一条牵挂（老人端）
EARN_DAILY_BONUS = 10     # 每日首次登录奖励

# AI 功能消耗
COST_GENERATE_VIDEO = 50
COST_RESTORE_PHOTO = 30
COST_ANIMATE_PHOTO = 40


async def _get_or_create_account(db: AsyncSession, user_id: UUID) -> UserPointAccount:
    """获取或自动创建用户积分账户。"""
    result = await db.execute(
        select(UserPointAccount).where(UserPointAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        account = UserPointAccount(user_id=user_id, total_points=0, available_points=0)
        db.add(account)
        await db.flush()
    return account


async def get_balance(db: AsyncSession, user_id: UUID) -> dict:
    """查询用户积分余额。"""
    account = await _get_or_create_account(db, user_id)
    return {
        "total_points": account.total_points,
        "available_points": account.available_points,
    }


async def earn_points(
    db: AsyncSession,
    user_id: UUID,
    amount: int,
    category: str,
    description: str | None = None,
) -> UserPointTransaction:
    """为用户增加积分。"""
    account = await _get_or_create_account(db, user_id)
    account.total_points += amount
    account.available_points += amount
    await db.flush()

    tx = UserPointTransaction(
        user_id=user_id,
        tx_type="earn",
        amount=amount,
        balance_after=account.available_points,
        category=category,
        description=description,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    logger.info(f"用户 {user_id} 获得 {amount} 积分 [{category}]")
    return tx


async def spend_points(
    db: AsyncSession,
    user_id: UUID,
    amount: int,
    category: str,
    description: str | None = None,
) -> UserPointTransaction:
    """
    扣减积分。余额不足时抛出 ValueError。
    返回交易记录。
    """
    account = await _get_or_create_account(db, user_id)
    if account.available_points < amount:
        raise ValueError(f"积分不足，需要 {amount}，当前可用 {account.available_points}")

    account.available_points -= amount
    await db.flush()

    tx = UserPointTransaction(
        user_id=user_id,
        tx_type="spend",
        amount=amount,
        balance_after=account.available_points,
        category=category,
        description=description,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    logger.info(f"用户 {user_id} 消费 {amount} 积分 [{category}]")
    return tx


async def get_transactions(db: AsyncSession, user_id: UUID, limit: int = 50) -> list[UserPointTransaction]:
    """查询用户最近的积分流水。"""
    result = await db.execute(
        select(UserPointTransaction)
        .where(UserPointTransaction.user_id == user_id)
        .order_by(UserPointTransaction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def check_daily_bonus(db: AsyncSession, user_id: UUID) -> bool:
    """
    检查并发放每日登录奖励。
    如果今天还没有 daily_bonus 记录，则发放并返回 True。
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    result = await db.execute(
        select(func.count(UserPointTransaction.id)).where(
            UserPointTransaction.user_id == user_id,
            UserPointTransaction.category == "daily_bonus",
            UserPointTransaction.created_at >= today_start,
        )
    )
    count = result.scalar() or 0
    if count > 0:
        return False

    await earn_points(db, user_id, EARN_DAILY_BONUS, "daily_bonus", "每日登录奖励")
    return True
