from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class MomentCreate(BaseModel):
    elder_id: UUID
    content_type: str | None = None
    text_content: str | None = Field(default=None, max_length=2000)
    media_urls: list[str] | None = None
    is_ai_generated: bool = False
    poster_meta: dict | None = None


class MomentResponse(BaseModel):
    id: UUID
    sender_id: UUID
    elder_id: UUID
    content_type: str
    text_content: str | None
    media_urls: list | None
    is_ai_generated: bool
    poster_meta: dict | None = None
    created_at: datetime
    is_read: bool = False

    model_config = {"from_attributes": True}


class ViewRequest(BaseModel):
    view_duration: int | None = None


class ResponseCreate(BaseModel):
    response_type: str
    content: str | None = None


class ElderStatusResponse(BaseModel):
    elder_name: str | None
    today_read: bool
    last_active_text: str | None
    alert_paused_until: str | None = None


class ActivityDay(BaseModel):
    date: str
    label: str
    active: bool


class ActivityResponse(BaseModel):
    days: list[ActivityDay]
