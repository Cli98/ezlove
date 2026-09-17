"""
演示场景种子数据：在 seed_elders.py 基础上补充演示用的活动记录

主角：张奶奶（B 级，祥盛家园 3 号楼）+ 女儿张小红
情节：29 天良好记录 → 今天异常（无查看 + 食堂缺席）→ 告警触发
配角：3 名 C 级志愿者 + 若干积分任务

用法:
  cd backend && PYTHONPATH=. python seed_demo.py
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, text

from app.database import async_session
from app.models.user import User
from app.models.community import Community, CommunityElder, CommunityWorker
from app.models.care_relation import CareRelation
from app.models.care_moment import CareMoment
from app.models.view_event import ViewEvent
from app.models.canteen import CanteenRecord
from app.models.community_event import CommunityEvent
from app.models.alert import Alert
from app.models.volunteer import VolunteerProfile, HelpTask, PointTransaction


async def seed_demo():
    async with async_session() as db:
        community = (await db.execute(
            select(Community).where(Community.name == "溪东社区")
        )).scalar_one_or_none()
        if not community:
            print("请先运行 seed_elders.py 创建溪东社区数据")
            return

        existing = (await db.execute(
            select(User).where(User.nickname == "张奶奶（演示）")
        )).scalar_one_or_none()
        if existing:
            print("演示数据已存在，跳过")
            return

        now = datetime.now()
        cid = community.id

        # ── 1. 创建主角：张奶奶 ──
        grandma_id = uuid.uuid4()
        grandma = User(
            id=grandma_id,
            openid=f"demo_elder_{uuid.uuid4().hex[:8]}",
            role="elder",
            nickname="张奶奶（演示）",
            phone="13900001001",
        )
        db.add(grandma)
        await db.flush()

        worker = (await db.execute(
            select(CommunityWorker).where(
                CommunityWorker.community_id == cid,
                CommunityWorker.role_label == "网格员",
            ).limit(1)
        )).scalar_one()

        grandma_elder = CommunityElder(
            id=uuid.uuid4(),
            community_id=cid,
            elder_id=grandma_id,
            care_level="B",
            address="祥盛家园3号楼2单元301室",
            emergency_contact_name="张小红(女儿)",
            emergency_contact_phone="13900001002",
            health_notes="独居，子女在杭州市区工作，有轻度高血压，平时食堂吃饭",
            assigned_worker_id=worker.id,
        )
        db.add(grandma_elder)

        # ── 2. 创建女儿张小红 ──
        daughter_id = uuid.uuid4()
        daughter = User(
            id=daughter_id,
            openid=f"demo_family_{uuid.uuid4().hex[:8]}",
            role="family",
            nickname="张小红",
            phone="13900001002",
        )
        db.add(daughter)
        await db.flush()

        relation = CareRelation(
            id=uuid.uuid4(),
            family_user_id=daughter_id,
            elder_user_id=grandma_id,
            relation_label="女儿",
            invite_code="DEMO" + uuid.uuid4().hex[:4].upper(),
            alert_threshold=12,
            status="active",
        )
        db.add(relation)
        await db.flush()

        # ── 3. 29 天良好记录 ──
        print("生成 29 天历史数据...")
        for day_offset in range(29, 0, -1):
            day = now - timedelta(days=day_offset)
            morning = day.replace(hour=8, minute=random.randint(0, 30))
            evening = day.replace(hour=18, minute=random.randint(0, 30))

            # 女儿每天发 1-2 条牵挂
            moment = CareMoment(
                id=uuid.uuid4(),
                sender_id=daughter_id,
                elder_id=grandma_id,
                content_type="text",
                text_content=random.choice([
                    "妈，今天天气好，出去走走吧",
                    "妈，记得吃药哦",
                    "妈，周末我回来看你",
                    "妈，今天做了红烧肉，下次给你带",
                    "妈，早上好，注意保暖",
                    "妈，晚上早点休息",
                    "妈，看看我今天拍的花",
                    "妈，想你了",
                ]),
                created_at=morning,
            )
            db.add(moment)
            await db.flush()

            # 老人查看（上午发的通常中午前看）
            view_time = morning + timedelta(hours=random.uniform(1, 3))
            view = ViewEvent(
                id=uuid.uuid4(),
                moment_id=moment.id,
                viewer_id=grandma_id,
                viewed_at=view_time,
                view_duration=random.randint(15, 120),
            )
            db.add(view)

            # 报平安（大部分天有）
            if random.random() < 0.85:
                checkin = ViewEvent(
                    id=uuid.uuid4(),
                    moment_id=None,
                    viewer_id=grandma_id,
                    viewed_at=day.replace(hour=9, minute=random.randint(0, 59)),
                )
                db.add(checkin)

            # 食堂记录（每天午、晚 2 餐，张奶奶到场）
            for meal_hour in [11, 17]:
                meal_time = day.replace(hour=meal_hour, minute=30)
                # 获取几个随机老人 ID 凑食堂记录
                sample_elders = (await db.execute(
                    select(CommunityElder.elder_id).where(
                        CommunityElder.community_id == cid
                    ).limit(10)
                )).scalars().all()

                attendees = [{"elder_id": str(grandma_id), "name": "张奶奶", "present": True}]
                for eid in sample_elders[:5]:
                    attendees.append({
                        "elder_id": str(eid),
                        "name": "某老人",
                        "present": random.random() < 0.9,
                    })

                canteen = CanteenRecord(
                    id=uuid.uuid4(),
                    community_id=cid,
                    raw_text=f"{meal_time.strftime('%m/%d')} {'午' if meal_hour == 11 else '晚'}餐出勤",
                    source_format="text",
                    parsed_data={"meal_type": "午餐" if meal_hour == 11 else "晚餐", "attendees": attendees},
                    parsed_at=meal_time,
                    parse_status="success",
                    recorded_by=worker.id,
                    created_at=meal_time,
                )
                db.add(canteen)

        # ── 4. 今天：异常！──
        print("设置今日异常场景...")

        # 女儿今天也发了牵挂（但张奶奶没看）
        today_morning = now.replace(hour=7, minute=30, second=0, microsecond=0)
        today_moment = CareMoment(
            id=uuid.uuid4(),
            sender_id=daughter_id,
            elder_id=grandma_id,
            content_type="text",
            text_content="妈，今天下雨，别忘了带伞",
            created_at=today_morning,
        )
        db.add(today_moment)

        # 今天午餐食堂记录 —— 张奶奶缺席
        today_lunch = now.replace(hour=11, minute=30, second=0, microsecond=0)
        if today_lunch < now:
            sample_elders = (await db.execute(
                select(CommunityElder.elder_id).where(
                    CommunityElder.community_id == cid
                ).limit(10)
            )).scalars().all()

            lunch_attendees = [{"elder_id": str(grandma_id), "name": "张奶奶", "present": False}]
            for eid in sample_elders[:5]:
                lunch_attendees.append({
                    "elder_id": str(eid),
                    "name": "某老人",
                    "present": random.random() < 0.9,
                })

            today_canteen = CanteenRecord(
                id=uuid.uuid4(),
                community_id=cid,
                raw_text=f"{now.strftime('%m/%d')} 午餐出勤",
                source_format="text",
                parsed_data={"meal_type": "午餐", "attendees": lunch_attendees},
                parsed_at=today_lunch,
                parse_status="success",
                recorded_by=worker.id,
                created_at=today_lunch,
            )
            db.add(today_canteen)

        # 产生告警
        alert = Alert(
            id=uuid.uuid4(),
            elder_id=grandma_id,
            community_id=cid,
            alert_type="no_signal",
            alert_level="warning",
            message="张奶奶（演示） 超过18小时无任何活动信号",
            trigger_rule="no_signal",
            assigned_worker_id=worker.id,
            response_deadline=now + timedelta(minutes=30),
            care_relation_id=relation.id,
        )
        db.add(alert)

        # 食堂缺席事件
        absent_event = CommunityEvent(
            id=uuid.uuid4(),
            community_id=cid,
            elder_id=grandma_id,
            event_type="absent",
            source="canteen",
            description="张奶奶（演示） 午餐未到食堂就餐",
            severity="warning",
        )
        db.add(absent_event)

        # ── 5. 志愿者 + 积分任务 ──
        print("创建志愿者和积分数据...")

        # 找 3 个 C 级老人作为志愿者
        c_elders = (await db.execute(
            select(CommunityElder).where(
                CommunityElder.community_id == cid,
                CommunityElder.care_level == "C",
            ).limit(3)
        )).scalars().all()

        volunteer_profiles = []
        for i, ce in enumerate(c_elders):
            elder_user = (await db.execute(
                select(User).where(User.id == ce.elder_id)
            )).scalar_one()

            vp = VolunteerProfile(
                id=uuid.uuid4(),
                elder_id=ce.id,
                user_id=ce.elder_id,
                community_id=cid,
                total_points=random.choice([30, 50, 80]),
                available_points=random.choice([20, 40, 60]),
                is_active=True,
            )
            db.add(vp)
            await db.flush()
            volunteer_profiles.append((vp, elder_user.nickname))

        # 创建已完成和待接的任务
        task_templates = [
            ("探访张奶奶", "visit", grandma_elder.id, 15),
            ("陪李大爷去医院", "accompany", None, 20),
            ("帮赵奶奶取快递", "errand", None, 10),
            ("签到：祥盛家园 3 号楼", "check_in", None, 5),
            ("探访王大爷", "visit", None, 15),
        ]

        for j, (title, ttype, target, points) in enumerate(task_templates):
            if j < 2:
                vp, vname = volunteer_profiles[j % len(volunteer_profiles)]
                task = HelpTask(
                    id=uuid.uuid4(),
                    community_id=cid,
                    title=title,
                    task_type=ttype,
                    target_elder_id=target,
                    point_value=points,
                    volunteer_id=vp.id,
                    assigned_by=worker.id,
                    status="verified",
                    completed_at=now - timedelta(days=random.randint(1, 7)),
                    verified_by=worker.id,
                    verified_at=now - timedelta(days=random.randint(0, 3)),
                )
                db.add(task)
                await db.flush()

                pt = PointTransaction(
                    id=uuid.uuid4(),
                    volunteer_id=vp.id,
                    transaction_type="earn",
                    amount=points,
                    balance_after=vp.available_points,
                    reference_type="task",
                    reference_id=task.id,
                    description=f"完成任务：{title}",
                )
                db.add(pt)
            else:
                task = HelpTask(
                    id=uuid.uuid4(),
                    community_id=cid,
                    title=title,
                    task_type=ttype,
                    target_elder_id=target,
                    point_value=points,
                    assigned_by=worker.id,
                    status="pending",
                )
                db.add(task)

        await db.commit()

        print("=" * 50)
        print("演示数据创建完成!")
        print("=" * 50)
        print(f"  主角: 张奶奶（演示）(ID: {grandma_id})")
        print(f"  女儿: 张小红 (ID: {daughter_id})")
        print(f"  邀请码: {relation.invite_code}")
        print(f"  29 天正常记录 + 今日异常（未查看 + 食堂缺席）")
        print(f"  告警已触发: {alert.id}")
        print(f"  志愿者: {len(volunteer_profiles)} 人")
        print(f"  任务: 2 已完成 + 3 待接")


if __name__ == "__main__":
    asyncio.run(seed_demo())
