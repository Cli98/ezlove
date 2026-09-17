from datetime import datetime, date

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.view_event import ViewEvent
from app.schemas.user import UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(data: UserUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/check-in")
async def self_check_in(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    event = ViewEvent(viewer_id=user.id, moment_id=None)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"ok": True, "checked_in_at": event.viewed_at.isoformat()}


@router.get("/check-in/today")
async def get_today_check_in(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today_start = datetime.combine(date.today(), datetime.min.time())
    result = await db.execute(
        select(ViewEvent.viewed_at)
        .where(ViewEvent.viewer_id == user.id, ViewEvent.moment_id.is_(None), ViewEvent.viewed_at >= today_start)
        .order_by(ViewEvent.viewed_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return {"checked_in": row is not None, "checked_in_at": row.isoformat() if row else None}
