"""积分相关 API 路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.services import points as points_service
from app.schemas.points import PointBalanceResponse, PointHistoryResponse, PointTxItem

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/balance", response_model=PointBalanceResponse)
async def get_point_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户积分余额。"""
    return await points_service.get_balance(db, user.id)


@router.get("/history", response_model=PointHistoryResponse)
async def get_point_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户积分流水（最近 50 条）。"""
    txs = await points_service.get_transactions(db, user.id)
    return PointHistoryResponse(
        transactions=[PointTxItem.model_validate(tx) for tx in txs]
    )
