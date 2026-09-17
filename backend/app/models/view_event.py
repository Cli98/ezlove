import uuid
from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ViewEvent(Base):
    __tablename__ = "view_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    moment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("care_moments.id"), nullable=True)
    viewer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    viewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    view_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
