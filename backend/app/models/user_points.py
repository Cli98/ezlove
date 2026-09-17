"""用户积分账户模型 — 独立于志愿者积分体系，面向全量用户的通用积分。"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class UserPointAccount(Base):
    """用户积分账户，每人一行，记录累计与可用积分。"""
    __tablename__ = "user_point_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)
    available_points = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())


class UserPointTransaction(Base):
    """积分流水：每笔收入/支出一条记录。"""
    __tablename__ = "user_point_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tx_type = Column(String(8), nullable=False)          # "earn" | "spend"
    amount = Column(Integer, nullable=False)              # 正整数
    balance_after = Column(Integer, nullable=False)       # 变动后的 available_points
    category = Column(String(32), nullable=True)          # send_moment / daily_bonus / ai_video / ai_restore / ai_animate
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
