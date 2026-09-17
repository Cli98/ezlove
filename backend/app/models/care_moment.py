import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CareMoment(Base):
    __tablename__ = "care_moments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    elder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    content_type: Mapped[str] = mapped_column(String(16), default="text")
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_urls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    poster_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
