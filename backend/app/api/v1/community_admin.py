"""社区数据维护端点（运维专用，一次性数据治理）

用途：
- elders-export-full：流式导出本社区老人及全部关联数据（NDJSON 备份，先备份后清理）
- elders-purge：按外键依赖顺序清理本社区全部老人及其关联数据（需 confirm_count 数量确认）
- elders-import：批量导入真实老人名单（幂等：同名同地址自动跳过；楼栋自动分配网格员）

安全：全部端点要求管理后台 worker JWT（get_current_worker），且仅作用于当前社区。
"""
import json
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, distinct, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_worker
from app.models.alert import Alert
from app.models.canteen import CanteenRecord
from app.models.care_moment import CareMoment
from app.models.care_relation import CareRelation
from app.models.community import CommunityElder, CommunityWorker
from app.models.community_event import CommunityEvent
from app.models.response import Response
from app.models.risk_snapshot import RiskScoreSnapshot
from app.models.user import User
from app.models.user_points import UserPointAccount, UserPointTransaction
from app.models.view_event import ViewEvent
from app.models.volunteer import HelpTask, PointTransaction, VolunteerProfile

router = APIRouter(prefix="/community/admin", tags=["community-admin"])

# 楼栋 → 网格员姓名（沿用 seed_elders.py 的网格划分；导入时按姓名匹配工作人员）
BUILDING_GRID_WORKER = {
    "祥盛家园1号楼": "张建国", "祥盛家园2号楼": "张建国",
    "祥盛家园3号楼": "张建国", "祥盛家园4号楼": "张建国",
    "祥盛家园5号楼": "王秀英", "祥盛家园6号楼": "王秀英",
    "祥盛家园7号楼": "王秀英", "祥盛家园8号楼": "王秀英",
    "祥盛家园9号楼": "刘志强", "祥盛家园10号楼": "刘志强",
    "祥盛家园11号楼": "刘志强", "祥盛家园12号楼": "刘志强",
    "祥盛家园13号楼": "赵桂兰", "祥盛家园14号楼": "赵桂兰",
    "祥盛家园15号楼": "赵桂兰",
    "祥盛家园16号楼": "孙永林", "祥盛家园17号楼": "孙永林",
    "祥盛家园18号楼": "孙永林", "祥盛家园19号楼": "孙永林",
    "南北乐章1号楼": "周玉珍", "南北乐章2号楼": "周玉珍",
    "南北乐章3号楼": "周玉珍", "南北乐章4号楼": "周玉珍",
    "南北乐章5号楼": "吴德明", "南北乐章6号楼": "吴德明",
    "南北乐章7号楼": "吴德明", "南北乐章8号楼": "吴德明",
    "桂花溪园1号楼": "徐淑芳", "桂花溪园2号楼": "徐淑芳",
    "桂花溪园3号楼": "徐淑芳", "桂花溪园4号楼": "徐淑芳",
    "桂花溪园5号楼": "徐淑芳", "桂花溪园6号楼": "徐淑芳",
}


def _ser(v):
    """datetime/date/UUID → JSON 可序列化值"""
    if isinstance(v, datetime):
        return v.isoformat(sep=" ")
    if isinstance(v, (date, uuid.UUID)):
        return str(v)
    return v


def _row_dict(row) -> dict:
    """行 → dict；ORM 实体展开为纯列值"""
    out = {}
    for k, v in row._mapping.items():
        if hasattr(v, "__table__"):  # SQLAlchemy ORM 实例
            out.update({c.name: _ser(getattr(v, c.name)) for c in v.__table__.columns})
        else:
            out[k] = _ser(v)
    return out


async def _collect_scope(db: AsyncSession, community_id: uuid.UUID) -> dict:
    """收集清理/导出范围：本社区老人用户、档案、牵挂、志愿者档案等 ID 集合"""
    elder_user_ids = [
        r[0] for r in (await db.execute(
            select(CommunityElder.elder_id).where(CommunityElder.community_id == community_id)
        )).all()
    ]
    elder_record_ids = [
        r[0] for r in (await db.execute(
            select(CommunityElder.id).where(CommunityElder.community_id == community_id)
        )).all()
    ]
    moment_ids = [
        r[0] for r in (await db.execute(
            select(CareMoment.id).where(CareMoment.elder_id.in_(elder_user_ids))
        )).all()
    ] if elder_user_ids else []
    vp_ids = [
        r[0] for r in (await db.execute(
            select(VolunteerProfile.id).where(VolunteerProfile.elder_id.in_(elder_record_ids))
        )).all()
    ] if elder_record_ids else []
    family_ids = [
        r[0] for r in (await db.execute(
            select(distinct(CareRelation.family_user_id)).where(CareRelation.elder_user_id.in_(elder_user_ids))
        )).all()
    ] if elder_user_ids else []
    return {
        "elder_user_ids": elder_user_ids,
        "elder_record_ids": elder_record_ids,
        "moment_ids": moment_ids,
        "vp_ids": vp_ids,
        "family_ids": family_ids,
    }


def _export_specs(scope: dict, community_id: uuid.UUID) -> list[tuple[str, object]]:
    """导出表清单: (表名, select 语句)"""
    eu = scope["elder_user_ids"]
    er = scope["elder_record_ids"]
    mo = scope["moment_ids"]
    vp = scope["vp_ids"]
    fam = scope["family_ids"]
    return [
        ("users", select(User).where(or_(User.id.in_(eu), User.id.in_(fam)))),
        ("community_elders", select(CommunityElder).where(CommunityElder.community_id == community_id)),
        ("care_relations", select(CareRelation).where(CareRelation.elder_user_id.in_(eu))),
        ("care_moments", select(CareMoment).where(CareMoment.elder_id.in_(eu))),
        ("view_events", select(ViewEvent).where(ViewEvent.viewer_id.in_(eu))),
        ("responses", select(Response).where(Response.responder_id.in_(eu))),
        ("alerts", select(Alert).where(Alert.elder_id.in_(eu))),
        ("community_events", select(CommunityEvent).where(CommunityEvent.elder_id.in_(eu))),
        ("risk_score_snapshots", select(RiskScoreSnapshot).where(RiskScoreSnapshot.elder_id.in_(er))),
        ("user_point_accounts", select(UserPointAccount).where(UserPointAccount.user_id.in_(eu))),
        ("user_point_transactions", select(UserPointTransaction).where(UserPointTransaction.user_id.in_(eu))),
        ("canteen_records", select(CanteenRecord).where(CanteenRecord.community_id == community_id)),
        ("volunteer_profiles", select(VolunteerProfile).where(VolunteerProfile.elder_id.in_(er))),
        ("help_tasks", select(HelpTask).where(or_(HelpTask.target_elder_id.in_(er), HelpTask.volunteer_id.in_(vp)))),
        ("point_transactions", select(PointTransaction).where(PointTransaction.volunteer_id.in_(vp))),
    ]


@router.get("/elders-export-full")
async def export_full(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """流式导出本社区老人及全部关联数据（NDJSON：首行 meta，末行 summary）"""
    community_id = worker.community_id
    scope = await _collect_scope(db, community_id)
    specs = _export_specs(scope, community_id)
    community_name = worker.name

    async def gen():
        meta = {
            "type": "meta",
            "community_id": str(community_id),
            "community_name": community_name,
            "exported_at": datetime.now().isoformat(sep=" "),
            "scope": {k: len(v) for k, v in scope.items()},
        }
        yield json.dumps(meta, ensure_ascii=False) + "\n"
        counts = {}
        for table, stmt in specs:
            n = 0
            result = await db.stream(stmt)
            async for row in result:
                yield json.dumps({"type": "row", "table": table, "row": _row_dict(row)}, ensure_ascii=False) + "\n"
                n += 1
            counts[table] = n
        yield json.dumps({"type": "summary", "counts": counts}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="elders-export-full.ndjson"'},
    )


class PurgeRequest(BaseModel):
    confirm_count: int


async def _delete_in(db: AsyncSession, model, column, ids: list) -> int:
    if not ids:
        return 0
    r = await db.execute(delete(model).where(column.in_(ids)))
    return r.rowcount or 0


@router.post("/elders-purge")
async def purge_elders(
    data: PurgeRequest,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """清理本社区全部老人及其关联数据（保留工作者、家属账号、社区本身）"""
    community_id = worker.community_id
    actual = len((await db.execute(
        select(CommunityElder.id).where(CommunityElder.community_id == community_id)
    )).all())
    if data.confirm_count != actual:
        raise HTTPException(status_code=400, detail=f"确认数量不匹配：当前档案数 {actual}，请求 {data.confirm_count}")

    scope = await _collect_scope(db, community_id)
    eu, er, mo, vp = scope["elder_user_ids"], scope["elder_record_ids"], scope["moment_ids"], scope["vp_ids"]

    deleted = {}
    # 按外键依赖顺序：先删从表，最后删主表
    deleted["point_transactions"] = await _delete_in(db, PointTransaction, PointTransaction.volunteer_id, vp)
    deleted["help_tasks"] = (
        await _delete_in(db, HelpTask, HelpTask.target_elder_id, er)
        + await _delete_in(db, HelpTask, HelpTask.volunteer_id, vp)
    )
    deleted["volunteer_profiles"] = await _delete_in(db, VolunteerProfile, VolunteerProfile.elder_id, er)
    deleted["risk_score_snapshots"] = await _delete_in(db, RiskScoreSnapshot, RiskScoreSnapshot.elder_id, er)
    deleted["alerts"] = await _delete_in(db, Alert, Alert.elder_id, eu)
    deleted["responses"] = (
        await _delete_in(db, Response, Response.responder_id, eu)
        + await _delete_in(db, Response, Response.moment_id, mo)
    )
    deleted["view_events"] = (
        await _delete_in(db, ViewEvent, ViewEvent.viewer_id, eu)
        + await _delete_in(db, ViewEvent, ViewEvent.moment_id, mo)
    )
    deleted["care_moments"] = (
        await _delete_in(db, CareMoment, CareMoment.elder_id, eu)
        + await _delete_in(db, CareMoment, CareMoment.sender_id, eu)
    )
    deleted["care_relations"] = await _delete_in(db, CareRelation, CareRelation.elder_user_id, eu)
    deleted["community_events"] = await _delete_in(db, CommunityEvent, CommunityEvent.elder_id, eu)
    r = await db.execute(delete(CanteenRecord).where(CanteenRecord.community_id == community_id))
    deleted["canteen_records"] = r.rowcount or 0
    deleted["user_point_transactions"] = await _delete_in(db, UserPointTransaction, UserPointTransaction.user_id, eu)
    deleted["user_point_accounts"] = await _delete_in(db, UserPointAccount, UserPointAccount.user_id, eu)
    r = await db.execute(delete(CommunityElder).where(CommunityElder.community_id == community_id))
    deleted["community_elders"] = r.rowcount or 0
    # 仅删除角色为 elder 的用户（家属账号保留，仅解除绑定）
    r = await db.execute(delete(User).where(User.id.in_(eu), User.role == "elder")) if eu else None
    deleted["users"] = (r.rowcount or 0) if r else 0

    await db.commit()
    return {"ok": True, "deleted": deleted, "family_kept": len(scope["family_ids"])}


class ImportElderItem(BaseModel):
    name: str
    address: str
    phone: str | None = None
    care_level: str = "B"
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    health_notes: str | None = None
    building_key: str | None = None


class ImportRequest(BaseModel):
    elders: list[ImportElderItem]
    dry_run: bool = False


@router.post("/elders-import")
async def import_elders(
    data: ImportRequest,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """批量导入真实老人名单（幂等：同名+同地址已存在则跳过；楼栋自动分配网格员）"""
    community_id = worker.community_id

    # 本社区现有 (姓名, 地址) 集合，用于幂等去重
    existing = {
        (nickname, address)
        for nickname, address in (await db.execute(
            select(User.nickname, CommunityElder.address)
            .join(User, CommunityElder.elder_id == User.id)
            .where(CommunityElder.community_id == community_id)
        )).all()
    }

    # 网格员姓名 → id
    grid_workers = {
        name: wid for wid, name in (await db.execute(
            select(CommunityWorker.id, CommunityWorker.name).where(
                CommunityWorker.community_id == community_id,
                CommunityWorker.role_label == "网格员",
            )
        )).all()
    }

    created, skipped, preview = [], [], []
    for item in data.elders:
        if (item.name, item.address) in existing:
            skipped.append({"name": item.name, "address": item.address, "reason": "已存在"})
            continue
        worker_id = None
        if item.building_key:
            worker_name = BUILDING_GRID_WORKER.get(item.building_key)
            if worker_name:
                worker_id = grid_workers.get(worker_name)
        entry = {
            "name": item.name,
            "address": item.address,
            "care_level": item.care_level,
            "phone": item.phone,
            "assigned_worker": str(worker_id) if worker_id else None,
        }
        preview.append(entry)
        if data.dry_run:
            continue
        user = User(
            id=uuid.uuid4(),
            openid=f"import_{uuid.uuid4().hex[:20]}",
            role="elder",
            nickname=item.name,
            phone=item.phone,
        )
        db.add(user)
        await db.flush()
        db.add(CommunityElder(
            id=uuid.uuid4(),
            community_id=community_id,
            elder_id=user.id,
            care_level=item.care_level,
            address=item.address,
            emergency_contact_name=item.emergency_contact_name,
            emergency_contact_phone=item.emergency_contact_phone,
            health_notes=item.health_notes,
            assigned_worker_id=worker_id,
        ))
        await db.flush()
        existing.add((item.name, item.address))
        created.append(entry)

    if not data.dry_run:
        await db.commit()
    return {
        "ok": True,
        "dry_run": data.dry_run,
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created": created,
        "skipped": skipped,
        "preview": preview if data.dry_run else None,
    }


