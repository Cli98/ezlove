from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.deps import get_current_worker
from app.models.community import CommunityWorker
from app.schemas.alert import AlertRuleResponse, AlertRuleUpdate
from app.services import alert_rules as rules_service

router = APIRouter(prefix="/community", tags=["alert-rules"])


@router.get("/alert-rules", response_model=list[AlertRuleResponse])
async def list_rules(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    return await rules_service.list_rules(db, worker.community_id)


@router.post("/alert-rules/seed", response_model=list[AlertRuleResponse])
async def seed_rules(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    rules = await rules_service.seed_default_rules(db, worker.community_id)
    await db.commit()
    return rules


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(
    rule_id: UUID,
    data: AlertRuleUpdate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    try:
        rule = await rules_service.update_rule(db, rule_id, data.model_dump(exclude_unset=True))
        await db.commit()
        return rule
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
