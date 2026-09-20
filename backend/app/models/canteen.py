import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CanteenRecord(Base):
    __tablename__ = "canteen_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    raw_text: Mapped[str] = mapped_column(Text)
    source_format: Mapped[str] = mapped_column(String(16), default="text")  # text / excel / other
    parsed_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    parse_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / success / failed
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("community_workers.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, server_default=func.now())
