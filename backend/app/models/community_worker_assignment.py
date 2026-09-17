import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CommunityWorkerAssignment(Base):
    __tablename__ = "community_worker_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("community_workers.id"))
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    role_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
