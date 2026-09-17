import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CommunityEvent(Base):
    __tablename__ = "community_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(16))  # fall / absent / emergency / visit / other
    source: Mapped[str] = mapped_column(String(16))  # canteen / alert / manual
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info / warning / urgent
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_workers.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
