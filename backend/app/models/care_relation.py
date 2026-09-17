import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CareRelation(Base):
    __tablename__ = "care_relations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    elder_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    relation_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    invite_code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    alert_threshold: Mapped[int] = mapped_column(Integer, default=12)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    alert_paused_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
