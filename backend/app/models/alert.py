import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    care_relation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("care_relations.id"), nullable=True)
    elder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    community_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("communities.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(16))
    alert_level: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_worker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("community_workers.id"), nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    response_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_rule: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
