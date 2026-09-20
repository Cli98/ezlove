"""非 fixture 数据构造辅助（P3 §3.9 契约）。

create_user / create_community / create_worker / worker_headers / auth_headers /
create_relation / create_moment / create_view_event / create_alert / create_community_elder
"""
import random
import string

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.care_moment import CareMoment
from app.models.care_relation import CareRelation
from app.models.community import Community, CommunityElder, CommunityWorker
from app.models.user import User
from app.models.view_event import ViewEvent
from app.services.auth import create_access_token


def _rand_suffix(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


async def create_user(db: AsyncSession, openid: str, role: str | None = None,
                      nickname: str | None = None) -> User:
    user = User(openid=openid, role=role, nickname=nickname)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_community(db: AsyncSession, name: str = "测试社区") -> Community:
    community = Community(name=name)
    db.add(community)
    await db.commit()
    await db.refresh(community)
    return community


async def create_worker(db: AsyncSession, community_id, name: str = "测试社工") -> CommunityWorker:
    # CommunityWorker 需关联一个 user；phone 唯一约束 → 随机；password_hash 任意合法串（不走登录）
    worker_user = await create_user(db, f"worker-user-{_rand_suffix()}")
    worker = CommunityWorker(
        user_id=worker_user.id,
        community_id=community_id,
        name=name,
        phone=f"1{_rand_suffix(10)}",
        password_hash="not-a-real-hash",
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return worker


def worker_headers(worker: CommunityWorker) -> dict:
    """管理后台 worker JWT——claims 结构与 community_auth.py 真实登录签发逐字段一致。"""
    token = create_access_token(
        worker.id,
        extra_claims={
            "type": "worker",
            "community_id": str(worker.community_id),
            "current_community_id": str(worker.community_id),
        },
    )
    return {"Authorization": f"Bearer {token}"}


async def auth_headers(client, openid: str) -> dict:
    """小程序侧 user token：POST /api/v1/auth/dev-login（用户需已存在，或由 get_or_create 创建）。"""
    resp = await client.post("/api/v1/auth/dev-login", json={"openid": openid})
    assert resp.status_code == 200, f"dev-login 失败: {resp.status_code} {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def create_relation(db: AsyncSession, family_id, elder_id,
                          status: str = "active", alert_threshold: int = 8) -> CareRelation:
    relation = CareRelation(
        family_user_id=family_id,
        elder_user_id=elder_id,
        invite_code=_rand_suffix(8),
        alert_threshold=alert_threshold,
        status=status,
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return relation


async def create_moment(db: AsyncSession, sender_id, elder_id,
                        created_at=None) -> CareMoment:
    # created_at 显式传值供测试构造相对时间；不传时走模型 Python default（不显式传 None）
    if created_at is not None:
        moment = CareMoment(
            sender_id=sender_id, elder_id=elder_id,
            content_type="text", text_content="测试牵挂内容", created_at=created_at,
        )
    else:
        moment = CareMoment(
            sender_id=sender_id, elder_id=elder_id,
            content_type="text", text_content="测试牵挂内容",
        )
    db.add(moment)
    await db.commit()
    await db.refresh(moment)
    return moment


async def create_view_event(db: AsyncSession, moment_id, viewer_id,
                            viewed_at=None) -> ViewEvent:
    # viewed_at 不传时走模型 Python default（不显式传 None，避免覆盖 default 写入 NULL）
    if viewed_at is not None:
        event = ViewEvent(moment_id=moment_id, viewer_id=viewer_id, viewed_at=viewed_at)
    else:
        event = ViewEvent(moment_id=moment_id, viewer_id=viewer_id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def create_alert(db: AsyncSession, **kwargs) -> Alert:
    """kwargs 直传模型字段（alert_level/response_deadline/is_resolved 等）。"""
    defaults = dict(alert_type="unread", alert_level="info", message="测试告警", is_resolved=False)
    defaults.update(kwargs)
    alert = Alert(**defaults)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def create_community_elder(db: AsyncSession, community_id, elder_user_id,
                                 care_level: str = "A") -> CommunityElder:
    record = CommunityElder(
        community_id=community_id, elder_id=elder_user_id, care_level=care_level,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
