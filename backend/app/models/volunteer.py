import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("community_elders.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    available_points: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class HelpTask(Base):
    __tablename__ = "help_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    title: Mapped[str] = mapped_column(String(128))
    task_type: Mapped[str] = mapped_column(String(16))  # visit / accompany / check_in / errand
    target_elder_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("community_elders.id"), nullable=True)
    point_value: Mapped[int] = mapped_column(Integer, default=10)
    volunteer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("volunteer_profiles.id"), nullable=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("community_workers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / accepted / completed / verified
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("community_workers.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class PointTransaction(Base):
    __tablename__ = "point_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    volunteer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("volunteer_profiles.id"))
    transaction_type: Mapped[str] = mapped_column(String(8))  # earn / spend
    amount: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    reference_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # task / redemption / adjustment
    reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
