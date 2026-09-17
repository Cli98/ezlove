import uuid
from datetime import date, datetime
from sqlalchemy import String, Date, ForeignKey, UniqueConstraint, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CanteenMenu(Base):
    __tablename__ = "canteen_menus"
    __table_args__ = (
        UniqueConstraint("community_id", "menu_date", "meal_type", name="uq_menu_per_day_meal"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communities.id"))
    menu_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(16), default="lunch")
    dishes: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    generated_by: Mapped[str] = mapped_column(String(16), default="ai")
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_workers.id"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
