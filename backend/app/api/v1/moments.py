from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, get_pagination
from app.models.user import User
from app.schemas.moment import MomentCreate, MomentResponse, ViewRequest, ResponseCreate
from app.schemas.pagination import PaginatedResponse
from app.services.moment import (
    create_moment, get_moments_for_user, count_moments_for_user, record_view,
    is_moment_read, batch_get_read_moment_ids, create_response,
)

router = APIRouter(prefix="/moments", tags=["moments"])


@router.post("", response_model=MomentResponse)
async def send_moment(data: MomentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    moment = await create_moment(
        db, sender_id=user.id, elder_id=data.elder_id,
        text_content=data.text_content, media_urls=data.media_urls,
        is_ai_generated=data.is_ai_generated,
        content_type=data.content_type, poster_meta=data.poster_meta,
    )
    return moment


@router.get("")
async def list_moments(
    pagination: dict = Depends(get_pagination),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = user.role or "family"
    total = await count_moments_for_user(db, user.id, role)
    moments = await get_moments_for_user(
        db, user.id, role,
        offset=pagination["offset"], limit=pagination["limit"],
    )
    # 批量查询已读状态，避免 N+1
    moment_ids = [m.id for m in moments]
    read_ids = await batch_get_read_moment_ids(db, moment_ids)
    result = []
    for m in moments:
        resp = MomentResponse.model_validate(m)
        resp.is_read = m.id in read_ids
        result.append(resp)
    return PaginatedResponse.create(
        items=result, total=total,
        page=pagination["page"], page_size=pagination["page_size"],
    )


@router.get("/{moment_id}", response_model=MomentResponse)
async def get_moment(moment_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.care_moment import CareMoment
    result = await db.execute(
        select(CareMoment).where(
            CareMoment.id == moment_id,
            (CareMoment.sender_id == user.id) | (CareMoment.elder_id == user.id),
        )
    )
    moment = result.scalar_one_or_none()
    if not moment:
        raise HTTPException(status_code=404, detail="内容不存在")
    read = await is_moment_read(db, moment.id)
    resp = MomentResponse.model_validate(moment)
    resp.is_read = read
    return resp


@router.post("/{moment_id}/view")
async def view_moment(
    moment_id: UUID, body: ViewRequest = None,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    duration = body.view_duration if body else None
    await record_view(db, moment_id, user.id, duration)
    return {"ok": True}


@router.post("/{moment_id}/response")
async def respond_to_moment(
    moment_id: UUID, data: ResponseCreate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    resp = await create_response(db, moment_id, user.id, data.response_type, data.content)
    return {"ok": True, "id": str(resp.id)}


@router.delete("/{moment_id}")
async def delete_moment(moment_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.care_moment import CareMoment
    result = await db.execute(select(CareMoment).where(CareMoment.id == moment_id, CareMoment.sender_id == user.id))
    moment = result.scalar_one_or_none()
    if not moment:
        raise HTTPException(status_code=404, detail="内容不存在")
    await db.delete(moment)
    await db.commit()
    return {"ok": True}
