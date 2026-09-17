from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=50)
    role: str | None = None
    avatar_url: str | None = None
    phone: str | None = None


class UserResponse(BaseModel):
    id: UUID
    openid: str
    nickname: str | None
    avatar_url: str | None
    role: str | None
    phone: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
