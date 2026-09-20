"""AC-7 时间口径与告警引擎用例（P3 §5 映射表；静态审计 + 集成 + 直调三型混合）。

直调对象：check_unread_alerts / run_alert_rules / _check_canteen（app.tasks.alert_checker）。
mock 对象：app.services.canteen.parse_canteen_text（就餐提交成功路径）。
"""
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.alert import Alert
from app.models.canteen import CanteenRecord
from app.models.care_moment import CareMoment
from app.models.community_event import CommunityEvent
from app.models.view_event import ViewEvent
from app.models.volunteer import HelpTask
from app.tasks.alert_checker import check_unread_alerts, run_alert_rules, _check_canteen
from app.utils import datetime as ez_dt

from tests.helpers import (
    auth_headers, create_alert, create_community, create_community_elder, create_moment,
    create_relation, create_user, create_view_event, create_worker, worker_headers,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

FIVE_MIN = timedelta(minutes=5)


# ── AC-7.1 时间字面量静态审计（P3 §6 冻结模式清单）──

async def test_time_literal_audit():
    """4 类模式全库扫描：①②零命中（工具自身白名单除外）、③④仅显式白名单。

    模式④断言为锚定注释级（P4-iter1 D6 收紧）：白名单文件的每个 date.today()
    调用处，其紧邻上一行必须是「# 审计白名单」开头的锚定注释——白名单文件内
    新增无锚定注释的 date.today() 误用必被本断言拦截（行号无关、不惧漂移）。
    """
    app_dir = Path(__file__).resolve().parents[1] / "app"

    hits_replace: set[str] = set()
    hits_combine: set[str] = set()
    hits_utcnow: set[str] = set()
    hits_today: set[str] = set()
    for py in app_dir.rglob("*.py"):
        src = py.read_text()
        rel = str(py.relative_to(app_dir))
        if "replace(hour=0" in src:
            hits_replace.add(rel)
        if "combine(date.today(" in src:
            hits_combine.add(rel)
        if "now(timezone.utc)" in src:
            hits_utcnow.add(rel)
        if "date.today()" in src:
            hits_today.add(rel)

    # 模式①：仅时间工具自身（today_start 的实现载体）
    assert hits_replace == {"utils/datetime.py"}
    # 模式②：零命中
    assert hits_combine == set()
    # 模式③：JWT 签发口径白名单（iat/exp 为 UTC 时间戳语义）
    assert hits_utcnow == {"services/auth.py"}
    # 模式④：date 业务语义白名单（canteen 当日菜单查询、菜单周起始、7 日日历序列，
    # 三处均为 date 值语义而非"今日零点"时刻，不适用 today_start() 改写）
    assert hits_today == {"api/v1/canteen.py", "services/canteen_menu.py",
                          "services/community_event.py"}

    # 模式④锚定注释收紧（D6）：逐行校验白名单文件的每个 date.today() 调用处——
    # 紧邻上一行必须是「# 审计白名单」开头的锚定注释，新增无锚定的调用必被拦截
    for rel in hits_today:
        lines = (app_dir / rel).read_text().splitlines()
        for i, line in enumerate(lines):
            if "date.today()" not in line:
                continue
            assert i > 0 and lines[i - 1].strip().startswith("# 审计白名单"), (
                f"{rel}:{i + 1} 的 date.today() 缺少紧邻上方的锚定注释——"
                "新增 date 值语义调用需加「# 审计白名单…」注释，且须确认是否真属白名单"
            )


# ── AC-7.2 跨端点"今日"口径一致（共同信号源 ViewEvent）──

async def test_cross_endpoint_today_consistency(client, db):
    """今日查看→工作台 today_active=true 且小程序 status today_read=true；
    仅昨日查看→两端均 false（单源 ViewEvent，两端同口径）。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    family = await create_user(db, "family-t1", role="family")
    elder = await create_user(db, "elder-t1", role="elder")
    await create_relation(db, family.id, elder.id)
    record = await create_community_elder(db, community.id, elder.id, care_level="A")
    moment = await create_moment(db, family.id, elder.id)
    yesterday_23 = ez_dt.today_start() - timedelta(hours=1)  # 昨日 23:00（字面 naive）

    # 场景一：仅昨日查看 → 两端均 false
    await create_view_event(db, moment.id, elder.id, viewed_at=yesterday_23)
    full = (await client.get(
        f"/api/v1/community/elders/{record.id}/full", headers=worker_headers(worker)
    )).json()
    status = (await client.get(
        f"/api/v1/elders/{elder.id}/status", headers=await auth_headers(client, "family-t1")
    )).json()
    assert full["today_active"] is False
    assert status["today_read"] is False

    # 场景二：补今日查看 → 两端均 true
    await create_view_event(db, moment.id, elder.id, viewed_at=datetime.now())
    full2 = (await client.get(
        f"/api/v1/community/elders/{record.id}/full", headers=worker_headers(worker)
    )).json()
    status2 = (await client.get(
        f"/api/v1/elders/{elder.id}/status", headers=await auth_headers(client, "family-t1")
    )).json()
    assert full2["today_active"] is True
    assert status2["today_read"] is True


# ── AC-7.3 跨天盲区 + 49h 级别（直调 check_unread_alerts）──

async def test_cross_day_blind_spot(db):
    """created_at=min(now-(T+2h), 今日零点-1s) 的未读牵挂 → 产生 unread 告警。

    修复前实现限定"今日"牵挂，跨天未读（昨日/更早）永不进候选 → 盲区。
    """
    family = await create_user(db, "family-t2", role="family")
    elder = await create_user(db, "elder-t2", role="elder")
    rel = await create_relation(db, family.id, elder.id, alert_threshold=8)
    now = datetime.now()
    created_at = min(
        now - timedelta(hours=10),  # T+2h
        ez_dt.today_start() - timedelta(seconds=1),  # 今日零点-1s
    )
    await create_moment(db, family.id, elder.id, created_at=created_at)

    await check_unread_alerts()
    alerts = (await db.execute(
        select(Alert).where(Alert.care_relation_id == rel.id)
    )).scalars().all()
    assert len(alerts) == 1
    assert alerts[0].trigger_rule == "unread_timeout"
    assert alerts[0].alert_type == "unread"


async def test_49h_urgent(db):
    """49h 未读 → alert_level=urgent（≥48h 分支可达；修复前代码不可达）。"""
    family = await create_user(db, "family-t3", role="family")
    elder = await create_user(db, "elder-t3", role="elder")
    rel = await create_relation(db, family.id, elder.id, alert_threshold=8)
    await create_moment(db, family.id, elder.id, created_at=datetime.now() - timedelta(hours=49))

    await check_unread_alerts()
    alerts = (await db.execute(
        select(Alert).where(Alert.care_relation_id == rel.id)
    )).scalars().all()
    assert len(alerts) == 1
    assert alerts[0].alert_level == "urgent"


# ── AC-7.4 阈值内不告警 / 任一查看即抑制 / 24h 滚动去重 ──

async def test_today_under_threshold_no_alert(db):
    """未达阈值（2h < 8h）不告警。"""
    family = await create_user(db, "family-t4", role="family")
    elder = await create_user(db, "elder-t4", role="elder")
    await create_relation(db, family.id, elder.id, alert_threshold=8)
    await create_moment(db, family.id, elder.id, created_at=datetime.now() - timedelta(hours=2))

    await check_unread_alerts()
    alerts = (await db.execute(select(Alert))).scalars().all()
    assert alerts == []


async def test_any_view_suppresses(db):
    """老人查看任一未读（较早的仍未读）→ 不告警（查看即活跃口径）。"""
    family = await create_user(db, "family-t5", role="family")
    elder = await create_user(db, "elder-t5", role="elder")
    await create_relation(db, family.id, elder.id, alert_threshold=8)
    await create_moment(db, family.id, elder.id, created_at=datetime.now() - timedelta(hours=10))
    moment2 = await create_moment(db, family.id, elder.id, created_at=datetime.now() - timedelta(hours=9))
    await create_view_event(db, moment2.id, elder.id)  # 仅查看较新一条

    await check_unread_alerts()
    alerts = (await db.execute(select(Alert))).scalars().all()
    assert alerts == []


async def test_24h_dedup(db):
    """近 24h 已有未解决 unread 告警 → 不重复（滚动窗口口径）。"""
    family = await create_user(db, "family-t6", role="family")
    elder = await create_user(db, "elder-t6", role="elder")
    rel = await create_relation(db, family.id, elder.id, alert_threshold=8)
    await create_moment(db, family.id, elder.id, created_at=datetime.now() - timedelta(hours=10))
    await create_alert(
        db, care_relation_id=rel.id, alert_type="unread",
        created_at=datetime.now() - timedelta(hours=3),  # 24h 窗口内
    )

    await check_unread_alerts()
    alerts = (await db.execute(
        select(Alert).where(Alert.care_relation_id == rel.id)
    )).scalars().all()
    assert len(alerts) == 1  # 原有 1 条，未新增


# ── AC-7.5 三条 viewed_at INSERT 路径 ──

async def test_viewed_at_insert_paths(client, db):
    """老人 view moment / 家属代签 checkin / 用户自签 check-in 的 viewed_at 与 now 差 <5min。"""
    family = await create_user(db, "family-t7", role="family")
    elder = await create_user(db, "elder-t7", role="elder")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)

    # 路径 1：老人查看 moment
    resp1 = await client.post(
        f"/api/v1/moments/{moment.id}/view", headers=await auth_headers(client, "elder-t7")
    )
    assert resp1.status_code == 200
    # 路径 2：家属代签
    resp2 = await client.post(
        f"/api/v1/elders/{elder.id}/checkin", headers=await auth_headers(client, "family-t7")
    )
    assert resp2.status_code == 200
    # 路径 3：用户自签
    resp3 = await client.post(
        "/api/v1/users/check-in", headers=await auth_headers(client, "family-t7")
    )
    assert resp3.status_code == 200

    now = datetime.now()
    events = (await db.execute(select(ViewEvent.viewed_at))).scalars().all()
    assert len(events) == 3
    for viewed_at in events:
        assert abs(now - viewed_at) < FIVE_MIN


# ── AC-7.6 UPDATE 时间路径 + INSERT default 路径 ──

async def test_update_time_paths(client, db, monkeypatch):
    """volunteer complete/verify、canteen parsed_at、alert resolved_at、
    event resolved_at 四条 UPDATE 显式赋值路径与 now 差 <5min。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    # mock LLM 解析走成功路径（ attendees 可为空——本用例只断言时间路径）
    async def fake_parse(raw_text, elder_list):
        return {"attendees": [], "meal_type": "午餐"}
    monkeypatch.setattr("app.services.canteen.parse_canteen_text", fake_parse)

    # ① canteen submit → parsed_at
    resp_canteen = await client.post(
        "/api/v1/community/canteen/submit", data={"raw_text": "张三 出"},
        headers=worker_headers(worker),
    )
    assert resp_canteen.status_code == 200
    record = (await db.execute(select(CanteenRecord))).scalar_one()
    assert abs(datetime.now() - record.parsed_at) < FIVE_MIN

    # ② volunteer complete / verify
    vol_user = await create_user(db, "vol-t1", role="elder")
    await create_community_elder(db, community.id, vol_user.id, care_level="C")
    reg = await client.post(
        "/api/v1/volunteer/register", headers=await auth_headers(client, "vol-t1")
    )
    assert reg.status_code == 200
    task_resp = await client.post(
        "/api/v1/volunteer/admin/tasks",
        json={"title": "陪伴聊天", "task_type": "visit", "point_value": 10},
        headers=worker_headers(worker),
    )
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]
    await client.post(f"/api/v1/volunteer/tasks/{task_id}/accept",
                      headers=await auth_headers(client, "vol-t1"))
    done = await client.post(f"/api/v1/volunteer/tasks/{task_id}/complete",
                             headers=await auth_headers(client, "vol-t1"))
    assert done.status_code == 200
    task = await db.get(HelpTask, uuid.UUID(task_id))
    assert abs(datetime.now() - task.completed_at) < FIVE_MIN

    verified = await client.put(f"/api/v1/volunteer/admin/tasks/{task_id}/verify",
                                headers=worker_headers(worker))
    assert verified.status_code == 200
    await db.refresh(task)
    assert abs(datetime.now() - task.verified_at) < FIVE_MIN

    # ③ 家属 resolve 告警 → resolved_at
    family = await create_user(db, "family-t8", role="family")
    elder = await create_user(db, "elder-t8", role="elder")
    rel = await create_relation(db, family.id, elder.id)
    alert = await create_alert(db, care_relation_id=rel.id)
    resp_resolve = await client.put(
        f"/api/v1/alerts/{alert.id}/resolve", headers=await auth_headers(client, "family-t8")
    )
    assert resp_resolve.status_code == 200
    await db.refresh(alert)
    assert abs(datetime.now() - alert.resolved_at) < FIVE_MIN

    # ④ worker resolve 社区事件 → CommunityEvent.resolved_at
    event = CommunityEvent(
        community_id=community.id, elder_id=elder.id,
        event_type="visit", source="manual", description="上门探访", is_resolved=False,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    resp_event = await client.put(
        f"/api/v1/community/events/{event.id}/resolve", json={},
        headers=worker_headers(worker),
    )
    assert resp_event.status_code == 200
    await db.refresh(event)
    assert abs(datetime.now() - event.resolved_at) < FIVE_MIN


async def test_canteen_volunteer_insert_paths(client, db, monkeypatch):
    """INSERT default 路径（P1 §7.2 + P2 M-09① 就餐两条分开断言）：
    ① canteen submit → CanteenRecord.created_at（default，与 parsed_at 分开断言，F5-c）；
    ② worker 建任务 → HelpTask.created_at（default）。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)

    # ① canteen submit：mock 解析成功，INSERT 的 created_at 走模型 Python default
    async def fake_parse(raw_text, elder_list):
        return {"attendees": [], "meal_type": "午餐"}
    monkeypatch.setattr("app.services.canteen.parse_canteen_text", fake_parse)
    resp = await client.post(
        "/api/v1/community/canteen/submit", data={"raw_text": "午餐：张三 出"},
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200
    assert resp.json()["parse_status"] == "success"
    record = (await db.execute(select(CanteenRecord))).scalar_one()
    now = datetime.now()
    assert abs(now - record.created_at) < FIVE_MIN  # INSERT default（晨检 L412 窗口比较列）
    assert abs(now - record.parsed_at) < FIVE_MIN  # UPDATE 显式赋值（分开断言）

    # ② worker 建帮扶任务：INSERT 的 created_at 走模型 Python default
    task_resp = await client.post(
        "/api/v1/volunteer/admin/tasks",
        json={"title": "代买蔬菜", "task_type": "errand", "point_value": 10},
        headers=worker_headers(worker),
    )
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]
    task = await db.get(HelpTask, uuid.UUID(task_id))
    assert abs(datetime.now() - task.created_at) < FIVE_MIN


# ── AC-7.7 混合时区字面行比较口径 ──

async def test_mixed_timezone_literal_compare(client, db):
    """昨日 23:00 字面行不计入 today_read、今日 01:00 行计入；
    晨检窗口（CanteenRecord.created_at）同样字面值直比无换算。"""
    family = await create_user(db, "family-t9", role="family")
    elder = await create_user(db, "elder-t9", role="elder")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    elder_headers = await auth_headers(client, "elder-t9")
    family_headers_ = await auth_headers(client, "family-t9")

    # 昨日 23:00 行不计入
    await create_view_event(
        db, moment.id, elder.id, viewed_at=ez_dt.today_start() - timedelta(hours=1)
    )
    status = (await client.get(
        f"/api/v1/elders/{elder.id}/status", headers=family_headers_
    )).json()
    assert status["today_read"] is False

    # 今日 01:00 行计入
    await create_view_event(
        db, moment.id, elder.id, viewed_at=ez_dt.today_start() + timedelta(hours=1)
    )
    status2 = (await client.get(
        f"/api/v1/elders/{elder.id}/status", headers=family_headers_
    )).json()
    assert status2["today_read"] is True

    # 晨检就餐窗口：字面 naive created_at 与 now 直比（aware/naive 混比将抛 TypeError）
    community = await create_community(db)
    record_ce = await create_community_elder(db, community.id, elder.id, care_level="A")
    w = await create_worker(db, community.id)
    for _ in range(2):  # threshold=12h → meals_threshold=2，两条缺餐记录触发
        db.add(CanteenRecord(
            community_id=community.id, raw_text="测试",
            parse_status="success", recorded_by=w.id,
            parsed_data={"attendees": [{"elder_id": str(elder.id), "present": False}]},
            created_at=datetime.now() - timedelta(hours=2),
        ))
    await db.commit()
    triggered, msg = await _check_canteen(
        db, record_ce, community.id, threshold_hours=12, now=datetime.now()
    )
    assert triggered is True
    assert "未到食堂就餐" in msg


# ── AC-7.7 晨检窗口排除侧：存量 UTC 语义字面值行不进窗口（P5-iter2 D3）──

async def test_morning_window_excludes_utc_literal_rows(db):
    """created_at=今日零点-1h 的存量 UTC 语义字面值行不触发晨检就餐窗口。

    与 test_mixed_timezone_literal_compare 晨检段（计入侧：created_at=now-2h
    的行在 threshold=12h 窗口内触发 _check_canteen）配对，使晨检窗口计入/
    排除两侧行为均有直接断言（AC-7.7）：修复前 DB func.now() 产生的 UTC
    字面值比本地真实时刻早 8h（本地今日 07:00 的真实事件字面值=昨日 23:00
    =今日零点-1h）；窗口按字面值与 cutoff 直比、无任何时区换算——字面值
    早于 cutoff 的存量行被排除、不参与缺餐计数，口径与修复前一致
    （若发生时区换算，该行真实时刻≈今日 07:00 > cutoff，将被计入并触发）。
    """
    community = await create_community(db, name="晨检排除侧社区")
    elder = await create_user(db, "elder-t12", role="elder")
    record_ce = await create_community_elder(db, community.id, elder.id, care_level="A")
    w = await create_worker(db, community.id)
    # 存量 UTC 语义字面值：优先取「今日零点-1h」（=昨日 23:00）；跨零点边界
    # 运行时取 min 退化为相对构造（AC-7.3 同款防边界写法），恒早于 cutoff=now-1h
    utc_like_at = min(
        ez_dt.today_start() - timedelta(hours=1),
        datetime.now() - timedelta(hours=2),
    )
    db.add(CanteenRecord(
        community_id=community.id, raw_text="测试",
        parse_status="success", recorded_by=w.id,
        parsed_data={"attendees": [{"elder_id": str(elder.id), "present": False}]},
        created_at=utc_like_at,
    ))
    await db.commit()

    triggered, msg = await _check_canteen(
        db, record_ce, community.id, threshold_hours=1, now=datetime.now()
    )
    # 字面值早于 cutoff(now-1h) → 窗口内 0 行 absent（meals_threshold=1 也不触发）
    assert triggered is False
    assert msg == ""


# ── AC-7.8 三类 INSERT created_at default ──

async def test_insert_created_at_defaults(client, db):
    """run_alert_rules 产 Alert、POST /moments 产 CareMoment、
    worker POST /community/events 产 CommunityEvent——created_at 与 now 差 <5min
    （CanteenRecord/HelpTask 由 test_canteen_volunteer_insert_paths 承接）。"""
    now = datetime.now()

    # ① 直调 run_alert_rules 产 Alert（no_signal 规则触发）
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-t10", role="elder", nickname="钱爷爷")
    await create_community_elder(db, community.id, elder.id, care_level="A")
    from app.models.alert_rule import AlertRule
    db.add(AlertRule(
        community_id=community.id, care_level="A", rule_type="no_signal",
        threshold_hours=18, enabled=True,
    ))
    await db.commit()
    await run_alert_rules()
    alert = (await db.execute(
        select(Alert).where(Alert.elder_id == elder.id, Alert.trigger_rule == "no_signal")
    )).scalar_one()
    assert abs(now - alert.created_at) < FIVE_MIN

    # ② POST /moments 产 CareMoment
    family = await create_user(db, "family-t10", role="family")
    elder2 = await create_user(db, "elder-t11", role="elder")
    await create_relation(db, family.id, elder2.id)
    resp = await client.post(
        "/api/v1/moments",
        json={"elder_id": str(elder2.id), "text_content": "早上好"},
        headers=await auth_headers(client, "family-t10"),
    )
    assert resp.status_code == 200
    moment = (await db.execute(select(CareMoment))).scalar_one()
    assert abs(now - moment.created_at) < FIVE_MIN

    # ③ worker POST /community/events 产 CommunityEvent
    event_resp = await client.post(
        "/api/v1/community/events",
        json={"elder_id": str(elder.id), "event_type": "visit",
              "description": "例行探访", "severity": "info"},
        headers=worker_headers(worker),
    )
    assert event_resp.status_code == 200
    event = (await db.execute(select(CommunityEvent))).scalar_one()
    assert abs(now - event.created_at) < FIVE_MIN
