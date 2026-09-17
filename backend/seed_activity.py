"""
溪东社区 30 天历史活动数据

需在 seed_elders.py 之后执行。生成：
  - CareRelation: ~630 条（30% 老人有家属）
  - CareMoment + ViewEvent: 家属发送牵挂 + 老人查看
  - CanteenRecord: 每天 1 条含全体 attendees
  - CommunityEvent: 网格员走访 + 跌倒事件
  - Alert: 食堂缺勤 + 无信号告警
  - 最后调 recalculate_all 计算风险分

用法:
  cd backend && PYTHONPATH=. python seed_activity.py
"""
import asyncio
import random
import string
import uuid
from datetime import datetime, timedelta, date

from sqlalchemy import select, func

from app.database import async_session
from app.models.user import User
from app.models.community import Community, CommunityWorker, CommunityElder
from app.models.care_relation import CareRelation
from app.models.care_moment import CareMoment
from app.models.view_event import ViewEvent
from app.models.canteen import CanteenRecord
from app.models.community_event import CommunityEvent
from app.models.alert import Alert
from app.services.risk_scoring import recalculate_all

CARE_TEXTS = [
    "今天天气不错，出去走走吧～",
    "妈，今天吃了什么好吃的？",
    "爸，记得按时吃药哦！",
    "想你了，周末回来看你",
    "今天工作不太忙，想起你了",
    "天冷了，多穿点衣服",
    "看到一个视频想给你看看",
    "今天做了你爱吃的红烧肉",
    "孙子今天学会走路了！",
    "妈，身体怎么样？",
    "爸你今天有没有去下棋？",
    "我今天去菜市场买了你爱吃的橘子",
    "天气预报说明天有雨，少出门",
    "奶奶生日快乐！",
    "周末带孩子去公园了，拍了好多照片",
    "今天加班到很晚才回家",
    "妈你跟李阿姨去跳广场舞了没",
    "爸记得量血压",
    "给你买了新的保暖内衣，快递明天到",
    "今天包了饺子，下次回来做给你吃",
]

FAMILY_GIVEN_NAMES = [
    "小明", "晓峰", "建军", "海涛", "小红", "丽娟", "婷婷", "晓燕",
    "伟", "强", "磊", "洋", "芳", "娜", "敏", "静",
    "浩", "杰", "超", "鑫", "倩", "雪", "欣", "琳",
]

VISIT_NOTES = [
    "走访老人，状态良好，精神不错",
    "上门探望，老人在家，血压正常",
    "日常巡查，老人正在看电视",
    "走访确认，老人与邻居聊天",
    "入户走访，老人独自在家，已送午餐",
    "日常探望，老人坐在楼下晒太阳",
    "走访核实，老人身体无恙",
    "上门服务，协助老人整理药品",
    "走访关怀，老人情绪稳定",
    "巡查探望，已确认老人安全",
]


def gen_invite_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


async def seed_activity():
    async with async_session() as db:
        # 加载社区
        community = (await db.execute(
            select(Community).where(Community.name == "溪东社区")
        )).scalar_one_or_none()
        if not community:
            print("错误：溪东社区不存在，请先运行 seed_elders.py")
            return

        # 加载工作者
        workers = (await db.execute(
            select(CommunityWorker).where(CommunityWorker.community_id == community.id)
        )).scalars().all()
        if not workers:
            print("错误：没有工作者数据")
            return

        grid_workers = [w for w in workers if w.role_label == "网格员"]

        # 加载老人
        elders_result = await db.execute(
            select(CommunityElder, User.nickname)
            .join(User, CommunityElder.elder_id == User.id)
            .where(CommunityElder.community_id == community.id)
        )
        elders_rows = elders_result.all()
        if not elders_rows:
            print("错误：没有老人数据")
            return

        elders = [(row[0], row[1]) for row in elders_rows]
        elder_by_level = {"A": [], "B": [], "C": []}
        for elder, name in elders:
            elder_by_level[elder.care_level].append((elder, name))

        print(f"加载 {len(elders)} 位老人：A={len(elder_by_level['A'])}, B={len(elder_by_level['B'])}, C={len(elder_by_level['C'])}")

        # 清除旧活动数据
        print("\n清除旧活动数据...")
        from sqlalchemy import text
        await db.execute(text("DELETE FROM risk_score_snapshots"))
        await db.execute(text("DELETE FROM alerts"))
        await db.execute(text("DELETE FROM community_events"))
        await db.execute(text("DELETE FROM canteen_records"))
        await db.execute(text("DELETE FROM view_events"))
        await db.execute(text("DELETE FROM care_moments"))
        await db.execute(text("DELETE FROM care_relations"))
        await db.execute(text("DELETE FROM users WHERE role = 'family'"))
        await db.commit()
        print("旧数据清除完成")

        now = datetime.now()
        today = now.date()
        start_date = today - timedelta(days=30)
        current_hour = now.hour

        # ─── 1. CareRelation: 30% 有家属 ───
        print("\n生成家属关系...")
        family_rates = {"A": 0.15, "B": 0.10, "C": 0.35}
        relations = []
        family_users = []
        used_codes = set()

        pending_rels = []
        for level, rate in family_rates.items():
            pool = elder_by_level[level]
            count = int(len(pool) * rate)
            selected = random.sample(pool, count)
            for elder, elder_name in selected:
                surname = elder_name[0]
                rel_label = random.choice(["儿子", "女儿", "儿媳", "女婿"])
                given = random.choice(FAMILY_GIVEN_NAMES)
                fam_name = surname + given

                fam_user = User(
                    id=uuid.uuid4(),
                    openid=f"family_{uuid.uuid4().hex[:8]}",
                    role="family",
                    nickname=fam_name,
                    phone=f"1{random.randint(30,99):02d}{random.randint(10000000,99999999)}",
                )
                db.add(fam_user)
                family_users.append(fam_user)

                code = gen_invite_code()
                while code in used_codes:
                    code = gen_invite_code()
                used_codes.add(code)

                pending_rels.append((elder, fam_user, rel_label, code))

        await db.flush()

        for elder, fam_user, rel_label, code in pending_rels:
            rel = CareRelation(
                id=uuid.uuid4(),
                family_user_id=fam_user.id,
                elder_user_id=elder.elder_id,
                relation_label=rel_label,
                invite_code=code,
                alert_threshold=12,
                status="active",
                created_at=datetime(
                    start_date.year, start_date.month, start_date.day,
                    random.randint(8, 18), random.randint(0, 59),
                ),
            )
            db.add(rel)
            relations.append((rel, elder, fam_user))

        await db.flush()
        print(f"  创建 {len(relations)} 条家属关系, {len(family_users)} 个家属用户")

        # 构建 elder_id → [(relation, family_user)] 映射
        elder_family_map = {}
        for rel, elder, fam_user in relations:
            elder_family_map.setdefault(elder.elder_id, []).append((rel, fam_user))

        # ─── 2. CareMoment + ViewEvent ───
        print("\n生成牵挂内容和查看事件...")
        total_moments = 0
        total_views = 0

        for day_offset in range(31):
            d = start_date + timedelta(days=day_offset)
            is_today_moment = (d == today)
            moments_batch = []
            views_batch = []

            for rel, elder, fam_user in relations:
                if random.random() > 0.60:
                    continue
                count = random.choices([1, 2], weights=[0.7, 0.3])[0]
                for _ in range(count):
                    max_h = min(current_hour, 21) if is_today_moment else 21
                    if max_h < 8:
                        continue
                    hour = random.randint(8, max_h)
                    minute = random.randint(0, 59)
                    if is_today_moment and hour == current_hour and minute > now.minute:
                        minute = random.randint(0, max(0, now.minute))
                    moment_time = datetime(d.year, d.month, d.day, hour, minute)

                    moment = CareMoment(
                        id=uuid.uuid4(),
                        sender_id=fam_user.id,
                        elder_id=elder.elder_id,
                        content_type="text",
                        text_content=random.choice(CARE_TEXTS),
                        is_ai_generated=random.random() < 0.15,
                        created_at=moment_time,
                    )
                    moments_batch.append(moment)

                    if random.random() < 0.70:
                        delay_hours = random.uniform(0.5, 4) if is_today_moment else random.uniform(1, 8)
                        view_time = moment_time + timedelta(hours=delay_hours)
                        if view_time > now:
                            view_time = moment_time + timedelta(minutes=random.randint(5, 60))
                        if view_time <= now:
                            view = ViewEvent(
                                id=uuid.uuid4(),
                                moment_id=moment.id,
                                viewer_id=elder.elder_id,
                                viewed_at=view_time,
                                view_duration=random.randint(5, 120),
                            )
                            views_batch.append(view)

            for m in moments_batch:
                db.add(m)
            await db.flush()
            for v in views_batch:
                db.add(v)
            await db.flush()

            total_moments += len(moments_batch)
            total_views += len(views_batch)

        print(f"  CareMoment: {total_moments} 条")
        print(f"  ViewEvent (家属): {total_views} 条")

        # ─── 2b. 独立 ViewEvent: 自上而下生成，保证楼栋趋势有意义 ───
        print("\n生成独立活跃事件...")
        import re
        active_rates = {"A": 0.20, "B": 0.35, "C": 0.50}
        independent_views = 0

        # 按楼栋分组无家属老人
        building_elders: dict[str, list] = {}
        for elder, name in elders:
            if elder.elder_id in elder_family_map:
                continue
            match = re.match(r"(.+\d+号楼)", elder.address)
            bldg = match.group(1) if match else "其他"
            building_elders.setdefault(bldg, []).append((elder, name))

        # 31 天全局日系数：缓慢上升 + 周末下降 + 微小扰动
        day_factors = []
        for day_offset in range(31):
            d = start_date + timedelta(days=day_offset)
            trend = 0.88 + 0.12 * (day_offset / 30)
            weekend = 0.90 if d.weekday() >= 5 else 1.0
            noise = random.gauss(0, 0.008)
            day_factors.append(max(0.75, min(1.10, trend * weekend + noise)))

        # 每栋楼一个固定偏移（模拟楼栋间差异：社区活跃度、老人构成等）
        building_offsets = {b: random.gauss(0, 0.03) for b in building_elders}

        # 给每位老人一个固定的活跃排序值（活跃的老人总是排前面）
        for bldg, bldg_elders in building_elders.items():
            for elder, name in bldg_elders:
                elder._activity_rank = random.random()

        for day_offset in range(31):
            d = start_date + timedelta(days=day_offset)
            is_today = (d == today)
            max_hour = current_hour if is_today else 21
            if max_hour < 6:
                continue
            views_batch = []
            df = day_factors[day_offset]

            for bldg, bldg_elders in building_elders.items():
                # 自上而下：先算这栋楼今天的目标活跃人数
                level_counts = {"A": 0, "B": 0, "C": 0}
                for elder, name in bldg_elders:
                    level_counts[elder.care_level] += 1

                target_active = 0
                for level, count in level_counts.items():
                    rate = active_rates[level] * df * (1 + building_offsets[bldg])
                    target_active += int(round(count * min(0.95, rate)))

                # 按活跃排序值选人（排名靠前的老人更容易被选中，天天都是差不多那些人活跃）
                sorted_elders = sorted(bldg_elders, key=lambda x: x[0]._activity_rank)
                selected = sorted_elders[:target_active]

                for elder, name in selected:
                    count = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
                    for _ in range(count):
                        hour = random.randint(6, max_hour)
                        minute = random.randint(0, 59)
                        if is_today and (hour > current_hour or (hour == current_hour and minute > now.minute)):
                            continue
                        view = ViewEvent(
                            id=uuid.uuid4(),
                            moment_id=None,
                            viewer_id=elder.elder_id,
                            viewed_at=datetime(d.year, d.month, d.day, hour, minute),
                            view_duration=random.randint(5, 180),
                        )
                        views_batch.append(view)

            for v in views_batch:
                db.add(v)
            await db.flush()
            independent_views += len(views_batch)

        print(f"  ViewEvent (独立): {independent_views} 条")

        # ─── 3. CanteenRecord: 每天 1 条 ───
        print("\n生成食堂就餐记录...")
        canteen_rates = {"A": 0.25, "B": 0.40, "C": 0.55}
        recorder = workers[0]  # 站长记录

        # A 类老人连续缺勤模拟：随机选 10 个 A 类老人，给他们 3-5 天连续缺勤期
        a_absence_periods = {}
        a_pool = elder_by_level["A"]
        for elder, name in random.sample(a_pool, min(10, len(a_pool))):
            absence_start = random.randint(5, 25)
            absence_len = random.randint(3, 5)
            a_absence_periods[elder.elder_id] = set(range(absence_start, absence_start + absence_len))

        # 给每位老人一个固定的食堂习惯排序值
        elder_canteen_rank = {elder.elder_id: random.random() for elder, name in elders}

        canteen_days = 0
        for day_offset in range(31):
            d = start_date + timedelta(days=day_offset)
            is_today = (d == today)
            if is_today and current_hour < 11:
                continue

            df = day_factors[day_offset]
            attendees = []
            for elder, name in elders:
                base_rate = canteen_rates[elder.care_level]
                rate = min(0.90, base_rate * df)
                if elder.elder_id in a_absence_periods and day_offset in a_absence_periods[elder.elder_id]:
                    present = False
                else:
                    # 用固定排序值决定：排名靠前的老人总是来食堂
                    present = elder_canteen_rank[elder.elder_id] < rate
                attendees.append({
                    "elder_id": str(elder.elder_id),
                    "elder_name": name,
                    "present": present,
                })

            record = CanteenRecord(
                id=uuid.uuid4(),
                community_id=community.id,
                raw_text=f"{d.isoformat()} 午餐签到",
                source_format="text",
                parsed_data={
                    "date": d.isoformat(),
                    "meal_type": "午餐",
                    "attendees": attendees,
                },
                parsed_at=datetime(d.year, d.month, d.day, 13, 0),
                parse_status="success",
                recorded_by=recorder.id,
                created_at=datetime(d.year, d.month, d.day, 12, 0),
            )
            db.add(record)
            canteen_days += 1

        await db.flush()
        print(f"  CanteenRecord: {canteen_days} 条（每条含 {len(elders)} 个 attendees）")

        # ─── 4. CommunityEvent: 走访 + 跌倒 ───
        print("\n生成社区事件...")
        total_events = 0

        for day_offset in range(31):
            d = start_date + timedelta(days=day_offset)
            is_today = (d == today)
            max_visit_hour = min(current_hour, 16) if is_today else 16
            if max_visit_hour < 9:
                continue

            for gw in grid_workers:
                assigned_elders = [(e, n) for e, n in elders if e.assigned_worker_id == gw.id]
                if not assigned_elders:
                    continue
                visit_count = random.randint(3, 5)
                visited = random.sample(assigned_elders, min(visit_count, len(assigned_elders)))

                for elder, name in visited:
                    hour = random.randint(9, max_visit_hour)
                    event = CommunityEvent(
                        id=uuid.uuid4(),
                        community_id=community.id,
                        elder_id=elder.elder_id,
                        event_type="visit",
                        source="manual",
                        description=f"走访{name}：{random.choice(VISIT_NOTES)}",
                        severity="info",
                        is_resolved=True,
                        resolved_by=gw.id,
                        resolved_at=datetime(d.year, d.month, d.day, hour, 30),
                        created_at=datetime(d.year, d.month, d.day, hour, 0),
                    )
                    db.add(event)
                    total_events += 1

            if day_offset % 3 == 0:
                fall_count = random.randint(1, 3)
                fall_elders = random.sample(elder_by_level["A"], min(fall_count, len(elder_by_level["A"])))
                for elder, name in fall_elders:
                    max_fall_hour = min(current_hour, 20) if is_today else 20
                    if max_fall_hour < 6:
                        continue
                    hour = random.randint(6, max_fall_hour)
                    is_old = day_offset < 27
                    event = CommunityEvent(
                        id=uuid.uuid4(),
                        community_id=community.id,
                        elder_id=elder.elder_id,
                        event_type="fall",
                        source="manual",
                        description=f"{name}在家中跌倒，{'已处理送医检查' if is_old else '等待处理'}",
                        severity="urgent",
                        is_resolved=is_old,
                        resolved_by=elder.assigned_worker_id if is_old else None,
                        resolved_at=datetime(d.year, d.month, d.day, hour + 1, 0) if is_old else None,
                        created_at=datetime(d.year, d.month, d.day, hour, 0),
                    )
                    db.add(event)
                    total_events += 1

        await db.flush()
        print(f"  CommunityEvent: {total_events} 条")

        # ─── 5. Alert ───
        print("\n生成告警...")
        total_alerts = 0

        # 5a: 食堂连续缺勤告警（A/B 类连续 3 天以上未到）
        for elder_id, absence_days in a_absence_periods.items():
            if len(absence_days) >= 3:
                elder_rec = next((e for e, n in elders if e.elder_id == elder_id), None)
                if not elder_rec:
                    continue
                elder_name = next((n for e, n in elders if e.elder_id == elder_id), "未知")
                min_day = min(absence_days)
                alert_date = start_date + timedelta(days=min_day + 2)
                is_old = (today - alert_date).days > 3

                alert = Alert(
                    id=uuid.uuid4(),
                    elder_id=elder_id,
                    community_id=community.id,
                    alert_type="canteen_absence",
                    alert_level="warning",
                    message=f"{elder_name}连续{len(absence_days)}天食堂未到，请关注",
                    is_resolved=is_old,
                    resolved_at=datetime(alert_date.year, alert_date.month, alert_date.day, 14, 0) if is_old else None,
                    assigned_worker_id=elder_rec.assigned_worker_id,
                    escalation_level=0,
                    trigger_rule="canteen_absence",
                    created_at=datetime(alert_date.year, alert_date.month, alert_date.day, 12, 0),
                )
                db.add(alert)
                total_alerts += 1

        # 5b: 无信号告警（A/B 类超时未活跃）
        for elder, name in elder_by_level["A"] + elder_by_level["B"]:
            if random.random() > 0.25:
                continue
            day_offset = random.randint(3, 28)
            alert_date = start_date + timedelta(days=day_offset)
            is_old = (today - alert_date).days > 3

            threshold = 18 if elder.care_level == "A" else 24
            alert = Alert(
                id=uuid.uuid4(),
                elder_id=elder.elder_id,
                community_id=community.id,
                alert_type="no_signal",
                alert_level="critical" if elder.care_level == "A" else "warning",
                message=f"{name}超过{threshold}小时无活动信号",
                is_resolved=is_old,
                resolved_at=datetime(alert_date.year, alert_date.month, alert_date.day, 16, 0) if is_old else None,
                assigned_worker_id=elder.assigned_worker_id,
                escalation_level=1 if elder.care_level == "A" else 0,
                trigger_rule="morning_silence",
                created_at=datetime(alert_date.year, alert_date.month, alert_date.day, 8, 0),
            )
            db.add(alert)
            total_alerts += 1

        # 5c: 家属侧未读告警
        for rel, elder, fam_user in relations:
            if random.random() > 0.15:
                continue
            day_offset = random.randint(5, 28)
            alert_date = start_date + timedelta(days=day_offset)
            is_old = (today - alert_date).days > 3
            elder_name = next((n for e, n in elders if e.elder_id == elder.elder_id), "未知")

            alert = Alert(
                id=uuid.uuid4(),
                care_relation_id=rel.id,
                elder_id=elder.elder_id,
                alert_type="unread",
                alert_level="info",
                message=f"{elder_name}有未查看的牵挂内容，已超过12小时",
                is_resolved=is_old,
                resolved_at=datetime(alert_date.year, alert_date.month, alert_date.day, 20, 0) if is_old else None,
                trigger_rule="unread_timeout",
                created_at=datetime(alert_date.year, alert_date.month, alert_date.day, 10, 0),
            )
            db.add(alert)
            total_alerts += 1

        await db.flush()
        print(f"  Alert: {total_alerts} 条")

        await db.commit()
        print("\n数据写入完成，开始计算风险分数...")

        # ─── 6. 计算风险分数 ───
        async with async_session() as db2:
            count = await recalculate_all(db2, community.id)
            await db2.commit()
            print(f"  风险分数计算完成: {count} 位老人")

        # ─── 7. 生成 30 天风险快照 ───
        print("\n生成风险分数快照...")
        from app.models.risk_snapshot import RiskScoreSnapshot
        from sqlalchemy import delete
        async with async_session() as db3:
            await db3.execute(
                delete(RiskScoreSnapshot).where(RiskScoreSnapshot.community_id == community.id)
            )
            await db3.flush()

            all_elders = (await db3.execute(
                select(CommunityElder).where(CommunityElder.community_id == community.id)
            )).scalars().all()

            snapshot_count = 0
            for elder in all_elders:
                base_score = elder.risk_score or 30
                for day_offset in range(31):
                    d = start_date + timedelta(days=day_offset)
                    variation = random.randint(-8, 8)
                    score = max(0, min(100, base_score + variation))
                    if score <= 30:
                        level = "normal"
                    elif score <= 60:
                        level = "attention"
                    elif score <= 80:
                        level = "warning"
                    else:
                        level = "critical"
                    db3.add(RiskScoreSnapshot(
                        elder_id=elder.id,
                        community_id=community.id,
                        score=score,
                        level=level,
                        snapshot_date=d,
                    ))
                    snapshot_count += 1

                if snapshot_count % 10000 == 0:
                    await db3.flush()

            await db3.flush()
            await db3.commit()
            print(f"  风险快照: {snapshot_count} 条")

        print("\n" + "=" * 50)
        print("溪东社区活动数据生成完成!")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed_activity())
