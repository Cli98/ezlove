from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.community import Community, CommunityElder
from app.models.user import User
from app.models.view_event import ViewEvent
from app.schemas.user import (
    BindElderRecordByPhoneCodeRequest,
    BindElderRecordRequest,
    UserUpdate,
    UserResponse,
)
from app.utils import datetime as ez_dt
from app.utils import wechat

router = APIRouter(prefix="/users", tags=["users"])


def _mask_phone(phone: str | None) -> str | None:
    if not phone or len(phone) < 7:
        return None
    return f"{phone[:3]}****{phone[-4:]}"


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/community-record")
async def get_my_community_record(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """当前微信绑定的社区档案，供小程序「社区档案」页判断是否还需补授权手机号。"""
    row = (await db.execute(
        select(CommunityElder, Community)
        .join(Community, Community.id == CommunityElder.community_id)
        .where(CommunityElder.elder_id == user.id)
        .limit(1)
    )).first()
    return {
        "bound": row is not None,
        "record_id": str(row[0].id) if row else None,
        "community_name": row[1].name if row else None,
        "elder_name": user.nickname,
        "phone_masked": _mask_phone(user.phone),
    }


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
    today_start = ez_dt.today_start()
    result = await db.execute(
        select(ViewEvent.viewed_at)
        .where(ViewEvent.viewer_id == user.id, ViewEvent.moment_id.is_(None), ViewEvent.viewed_at >= today_start)
        .order_by(ViewEvent.viewed_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return {"checked_in": row is not None, "checked_in_at": row.isoformat() if row else None}


@router.post("/bind-elder-record")
async def bind_elder_record(
    data: BindElderRecordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """老人用手机号认领社区档案：把档案从导入账号迁到当前微信账号。"""
    return await _bind_record_to_user(db, user, data.phone.strip())


@router.post("/bind-elder-record/wx-phone")
async def bind_elder_record_by_wx_phone(
    data: BindElderRecordByPhoneCodeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """老人点一次「允许」授权微信手机号，系统自动匹配并绑定社区档案。

    档案已由社区后台代绑时不再报冲突，只把微信返回的手机号补写到账号上。
    """
    phone = await wechat.get_phone_number(data.code)
    if not phone:
        raise HTTPException(
            status_code=400,
            detail="未能获取微信手机号，请稍后重试或手动输入手机号",
        )
    return await _bind_record_to_user(db, user, phone, trusted=True)


async def _bind_record_to_user(db: AsyncSession, user: User, phone: str, trusted: bool = False) -> dict:
    """按手机号把导入档案迁到当前微信用户（手动输入与微信授权共用）。

    trusted=True 表示手机号由微信授权返回（可信），此时已绑定的账号只补写手机号，不重新匹配档案。
    """
    if user.role == "family":
        raise HTTPException(status_code=400, detail="当前为子女身份，请先切换到长辈身份再绑定")

    bound = (await db.execute(
        select(CommunityElder).where(CommunityElder.elder_id == user.id).limit(1)
    )).scalar_one_or_none()
    if bound is not None:
        if not trusted:
            raise HTTPException(status_code=409, detail="当前微信已绑定社区档案")
        # 社区后台代绑档案时拿不到手机号；老人自己授权一次就补上，后台名单才认得出是谁
        user.phone = phone
        await db.commit()
        community_name = (await db.execute(
            select(Community.name).where(Community.id == bound.community_id)
        )).scalar_one_or_none()
        return {
            "ok": True,
            "already_bound": True,
            "record_id": str(bound.id),
            "elder_name": user.nickname or "社区档案",
            "community_name": community_name,
            "phone_masked": _mask_phone(phone),
        }

    rows = (await db.execute(
        select(CommunityElder, User, Community)
        .join(User, User.id == CommunityElder.elder_id)
        .join(Community, Community.id == CommunityElder.community_id)
        .where(User.phone == phone)
    )).all()
    if not rows:
        raise HTTPException(status_code=404, detail="未找到该手机号对应的社区档案，请联系社区工作人员")
    if len(rows) > 1:
        raise HTTPException(status_code=400, detail="该手机号关联了多个档案，请联系社区工作人员")

    record, old_user, community = rows[0]
    # 只允许认领尚未接入真实微信的导入档案，避免抢占他人已绑定的档案
    if not (old_user.openid or "").startswith("import_"):
        raise HTTPException(status_code=409, detail="该档案已绑定其他微信账号")

    record.elder_id = user.id
    if not user.role:
        user.role = "elder"
    if not user.nickname:
        user.nickname = old_user.nickname
    if not user.phone:
        user.phone = phone
    await db.commit()

    return {
        "ok": True,
        "already_bound": False,
        "record_id": str(record.id),
        "elder_name": user.nickname or old_user.nickname,
        "community_name": community.name,
    }
