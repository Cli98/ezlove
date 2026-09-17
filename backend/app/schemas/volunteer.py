from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class VolunteerRegister(BaseModel):
    community_elder_id: UUID


class VolunteerProfileResponse(BaseModel):
    id: UUID
    elder_id: UUID
    user_id: UUID
    total_points: int
    available_points: int
    is_active: bool
    created_at: datetime
    elder_name: str | None = None


class HelpTaskCreate(BaseModel):
    title: str
    task_type: str
    target_elder_id: UUID | None = None
    point_value: int = 10
    notes: str | None = None


class HelpTaskResponse(BaseModel):
    id: UUID
    title: str
    task_type: str
    target_elder_id: UUID | None
    point_value: int
    volunteer_id: UUID | None
    status: str
    notes: str | None
    completed_at: datetime | None
    verified_at: datetime | None
    created_at: datetime
    volunteer_name: str | None = None
    target_elder_name: str | None = None


class PointTransactionResponse(BaseModel):
    id: UUID
    transaction_type: str
    amount: int
    balance_after: int
    reference_type: str | None
    description: str | None
    created_at: datetime


class LeaderboardEntry(BaseModel):
    volunteer_id: UUID
    elder_name: str | None
    total_points: int
    task_count: int
