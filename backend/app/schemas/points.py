"""积分相关请求/响应 Schema。"""
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class PointBalanceResponse(BaseModel):
    """积分余额。"""
    total_points: int
    available_points: int


class PointTxItem(BaseModel):
    """单条积分流水。"""
    id: UUID
    tx_type: str
    amount: int
    balance_after: int
    category: str | None = None
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PointHistoryResponse(BaseModel):
    """积分流水列表。"""
    transactions: list[PointTxItem]
