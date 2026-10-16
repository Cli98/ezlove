from pydantic import BaseModel


class ContributorResponse(BaseModel):
    name: str | None = None
    wechat_id: str
    note: str | None = None
