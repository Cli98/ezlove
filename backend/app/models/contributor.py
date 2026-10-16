import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Contributor(Base):
    """公益志愿同学（"联系我们"贡献页名单）"""

    __tablename__ = "contributors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    wechat_id: Mapped[str] = mapped_column(String(64), unique=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
