from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: UUID
    care_relation_id: UUID | None = None
    elder_id: UUID | None = None
    community_id: UUID | None = None
    alert_type: str
    alert_level: str
    message: str
    is_resolved: bool
    resolved_at: datetime | None = None
    assigned_worker_id: UUID | None = None
    escalation_level: int = 0
    response_deadline: datetime | None = None
    responded_at: datetime | None = None
    response_note: str | None = None
    trigger_rule: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertRespondRequest(BaseModel):
    response_note: str


class AlertRuleResponse(BaseModel):
    id: UUID
    community_id: UUID
    care_level: str
    rule_type: str
    threshold_hours: int
    enabled: bool
    config: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertRuleUpdate(BaseModel):
    threshold_hours: int | None = Field(default=None, ge=1, le=168)
    enabled: bool | None = None
    config: dict | None = None
