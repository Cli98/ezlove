from uuid import UUID

from pydantic import BaseModel


class ContributorResponse(BaseModel):
    id: UUID
    name: str | None = None
    wechat_id: str
    note: str | None = None
    sort_order: int = 0

    model_config = {"from_attributes": True}
