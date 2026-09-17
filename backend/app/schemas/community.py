from typing import Literal

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ElderCreate(BaseModel):
    elder_id: UUID
    care_level: Literal["A", "B", "C"]
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    health_notes: str | None = None
    assigned_worker_id: UUID | None = None


class ElderUpdate(BaseModel):
    care_level: Literal["A", "B", "C"] | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    health_notes: str | None = None
    assigned_worker_id: UUID | None = None


class ElderResponse(BaseModel):
    id: UUID
    community_id: UUID
    elder_id: UUID
    care_level: str
    address: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    health_notes: str | None
    assigned_worker_id: UUID | None
    created_at: datetime
    updated_at: datetime
    elder_name: str | None = None
    elder_phone: str | None = None
    today_active: bool = False
    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    total_elders: int
    level_a: int
    level_b: int
    level_c: int
    today_active_count: int
    today_active_rate: float
    pending_events: int
    heatmap: list[dict] = []
