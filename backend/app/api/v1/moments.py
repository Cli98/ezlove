from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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


async def _serialize_moments(db: AsyncSession, moments: list, read_ids: set[UUID]) -> list[MomentResponse]:
    participant_ids = {user_id for moment in moments for user_id in (moment.sender_id, moment.elder_id)}
    users = (await db.execute(
        select(User.id, User.nickname, User.avatar_url).where(User.id.in_(participant_ids))
    )).all() if participant_ids else []
    profiles = {user_id: (nickname, avatar_url) for user_id, nickname, avatar_url in users}

    result = []
    for moment in moments:
        response = MomentResponse.model_validate(moment)
        response.is_read = moment.id in read_ids
        response.sender_name, response.sender_avatar_url = profiles.get(moment.sender_id, (None, None))
        response.elder_name, response.elder_avatar_url = profiles.get(moment.elder_id, (None, None))
        result.append(response)
    return result


@router.post("", response_model=MomentResponse)
async def send_moment(data: MomentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "family":
        raise HTTPException(status_code=403, detail="仅家人可发送牵挂")
    try:
        moment = await create_moment(
            db, sender_id=user.id, elder_id=data.elder_id,
            text_content=data.text_content, media_urls=data.media_urls,
            is_ai_generated=data.is_ai_generated,
            content_type=data.content_type, poster_meta=data.poster_meta,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return moment


@router.get("")
async def list_moments(
    pagination: dict = Depends(get_pagination),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in {"family", "elder"}:
        raise HTTPException(status_code=403, detail="请先选择身份")
    role = user.role
    total = await count_moments_for_user(db, user.id, role)
    moments = await get_moments_for_user(
        db, user.id, role,
        offset=pagination["offset"], limit=pagination["limit"],
    )
    # 批量查询已读状态，避免 N+1
    moment_ids = [m.id for m in moments]
    read_ids = await batch_get_read_moment_ids(db, moment_ids)
    result = await _serialize_moments(db, moments, read_ids)
    return PaginatedResponse.create(
        items=result, total=total,
        page=pagination["page"], page_size=pagination["page_size"],
    )


@router.get("/{moment_id}", response_model=MomentResponse)
async def get_moment(moment_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
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
    read_ids = {moment.id} if await is_moment_read(db, moment.id, moment.elder_id) else set()
    return (await _serialize_moments(db, [moment], read_ids))[0]


@router.post("/{moment_id}/view")
async def view_moment(
    moment_id: UUID, body: ViewRequest = None,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    duration = body.view_duration if body else None
    try:
        # 家属查看（record_view 返回 None）仍返回 ok，仅不落查看记录（OP-4）
        await record_view(db, moment_id, user.id, duration)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}


@router.post("/{moment_id}/response")
async def respond_to_moment(
    moment_id: UUID, data: ResponseCreate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    try:
        resp = await create_response(db, moment_id, user.id, data.response_type, data.content)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
