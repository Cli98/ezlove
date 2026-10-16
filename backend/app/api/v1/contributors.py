from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.contributor import ContributorResponse
from app.services import contributor as contributor_service

router = APIRouter(prefix="/contributors", tags=["contributors"])


# 公益志愿同学贡献页名单：公开只读，小程序"联系我们"页与社区管理后台共用
@router.get("", response_model=list[ContributorResponse])
async def list_contributors(db: AsyncSession = Depends(get_db)):
    return await contributor_service.list_active_contributors(db)
