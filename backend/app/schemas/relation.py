from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class InviteResponse(BaseModel):
    invite_code: str


class BindRequest(BaseModel):
    invite_code: str


class RelationUpdate(BaseModel):
    relation_label: str | None = None
    alert_threshold: int | None = None
    alert_paused_until: datetime | None = None


class RelationResponse(BaseModel):
    id: UUID
    family_user_id: UUID
    elder_user_id: UUID | None
    relation_label: str | None
    elder_name: str | None = None
    alert_threshold: int
    alert_paused_until: datetime | None = None
    status: str
    today_read: bool = False
    last_active_text: str | None = None

    model_config = {"from_attributes": True}
