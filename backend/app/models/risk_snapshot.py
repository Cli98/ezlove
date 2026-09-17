import uuid
from datetime import datetime, date

from sqlalchemy import String, Integer, Date, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RiskScoreSnapshot(Base):
    __tablename__ = "risk_score_snapshots"
    __table_args__ = (
        UniqueConstraint("elder_id", "snapshot_date", name="uq_risk_snapshot_elder_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("community_elders.id"))
    community_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("communities.id"))
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(16))
    snapshot_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
