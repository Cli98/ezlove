from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.view_event import ViewEvent
from app.schemas.relation import InviteResponse, BindRequest, RelationUpdate, RelationResponse
from app.services.relation import create_invite, bind_by_code, get_relations

router = APIRouter(prefix="/relations", tags=["relations"])


@router.post("/invite", response_model=InviteResponse)
async def generate_invite(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    relation = await create_invite(db, user.id)
    return InviteResponse(invite_code=relation.invite_code)


@router.post("/bind", response_model=RelationResponse)
async def bind(req: BindRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        relation = await bind_by_code(db, user.id, req.invite_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return relation


@router.get("", response_model=list[RelationResponse])
async def list_relations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    relations = await get_relations(db, user.id)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    result = []
    for r in relations:
        resp = RelationResponse.model_validate(r)
        elder_id = r.elder_user_id
        if elder_id:
            # 查询老人昵称，用于前端展示
            elder_result = await db.execute(select(User.nickname).where(User.id == elder_id))
            resp.elder_name = elder_result.scalar_one_or_none()

            view_result = await db.execute(
                select(ViewEvent)
                .where(ViewEvent.viewer_id == elder_id, ViewEvent.viewed_at >= today_start)
                .limit(1)
            )
            resp.today_read = view_result.scalar_one_or_none() is not None

            last_result = await db.execute(
                select(ViewEvent.viewed_at)
                .where(ViewEvent.viewer_id == elder_id)
                .order_by(ViewEvent.viewed_at.desc())
                .limit(1)
            )
            last_active = last_result.scalar_one_or_none()
            if last_active:
                resp.last_active_text = last_active.strftime("%m月%d日 %H:%M")
        result.append(resp)
    return result


@router.put("/{relation_id}", response_model=RelationResponse)
async def update_relation(
    relation_id: UUID, data: RelationUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    from app.models.care_relation import CareRelation
    result = await db.execute(
        select(CareRelation).where(
            CareRelation.id == relation_id,
            (CareRelation.family_user_id == user.id) | (CareRelation.elder_user_id == user.id),
        )
    )
    relation = result.scalar_one_or_none()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(relation, field, value)
    await db.commit()
    await db.refresh(relation)
    return relation


@router.delete("/{relation_id}")
async def delete_relation(
    relation_id: UUID,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    from app.models.care_relation import CareRelation
    result = await db.execute(
        select(CareRelation).where(
            CareRelation.id == relation_id,
            (CareRelation.family_user_id == user.id) | (CareRelation.elder_user_id == user.id),
        )
    )
    relation = result.scalar_one_or_none()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")
    relation.status = "inactive"
    await db.commit()
    return {"ok": True}
