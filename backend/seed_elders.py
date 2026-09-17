"""
溪东社区种子数据：2101 位老人 + 15 名工作者

用法:
  cd backend && PYTHONPATH=. python seed_elders.py [--clean]

--clean: 清除所有现有社区/老人数据后重新生成
"""
import argparse
import asyncio
import random
import uuid

from passlib.context import CryptContext
from sqlalchemy import select, delete, text

from app.database import async_session
from app.models.user import User
from app.models.community import Community, CommunityWorker, CommunityElder

pwd_ctx = CryptContext(schemes=["bcrypt"])

SURNAMES = list("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐韩曹许邓萧冯曾程蔡彭潘袁董余苏叶吕魏蒋田杜丁沈姜范江傅钟卢汪戴崔任陆廖姚方金邱夏谭韦贾邹石熊孟秦阎薛侯雷白龙段郝孔邵史毛常万顾赖武康贺严尹钱施牛洪龚")

GIVEN_NAMES_M = [
    "建国", "国强", "志明", "永林", "德明", "文华", "正义", "明远", "天福", "长青",
    "金生", "福生", "宝林", "玉山", "大海", "光明", "家宝", "学文", "建华", "国庆",
    "振华", "锦荣", "世安", "永祥", "立功", "恒昌", "良平", "清河", "兴邦", "保国",
    "东升", "耀祖", "承恩", "润生", "树仁", "惠民", "启明", "根生", "庆丰", "定邦",
]
GIVEN_NAMES_F = [
    "秀英", "桂兰", "玉珍", "淑芳", "凤英", "秀珍", "翠花", "桂英", "玉兰", "美华",
    "春花", "金凤", "素芬", "丽华", "桂芳", "秀兰", "美珍", "玉芬", "凤兰", "淑华",
    "银花", "慧珍", "宝珠", "月琴", "彩云", "秀梅", "惠芳", "碧云", "巧兰", "瑞芳",
    "翠兰", "雪芬", "荷花", "素英", "慧兰", "明珠", "香莲", "云芳", "巧云", "丽珍",
]

HEALTH_NOTES_A = [
    "失能半自理，需要日常照护，子女不在身边",
    "认知障碍，独居，容易迷路，需重点看护",
    "高龄90+，行动不便，听力严重下降",
    "低保户，多种慢性病，独居无子女",
    "心脏病+糖尿病，独居，应急能力弱",
    "中风后遗症，行动受限，配偶年迈",
    "失智症早期，偶有走失风险",
    "骨折术后恢复期，暂时无法独立行动",
]
HEALTH_NOTES_B = [
    "空巢老人，子女在外地，每月来看一次",
    "独居，身体状况一般，有轻度高血压",
    "配偶已故，子女偶尔回来，平时独居",
    "腿脚不太方便，日常买菜需要帮助",
    "子女在杭州市区工作，周末偶尔探望",
    "独居，有慢性支气管炎，冬天容易发作",
    "轻度白内障，视力下降，出行需注意",
]
HEALTH_NOTES_C = [
    "身体健康，与老伴同住，经常参加社区活动",
    "退休教师，身体硬朗，热心志愿服务",
    "每天坚持散步锻炼，子女同住",
    "身体不错，是楼栋志愿者",
    "健康状况良好，积极参与互助活动",
    "与子女同住，能自理，偶尔帮带孙辈",
    "退休工人，喜欢下棋，身体无大碍",
    "热爱广场舞，社区活动积极分子",
]

AREAS = [
    {"name": "祥盛家园", "buildings": 19, "elders": 1100},
    {"name": "南北乐章", "buildings": 8, "elders": 600},
    {"name": "桂花溪园", "buildings": 6, "elders": 401},
]

WORKERS = [
    {"role_label": "站长", "name": "陈明华"},
    {"role_label": "副站长", "name": "李芳"},
    {"role_label": "网格员", "name": "张建国"},
    {"role_label": "网格员", "name": "王秀英"},
    {"role_label": "网格员", "name": "刘志强"},
    {"role_label": "网格员", "name": "赵桂兰"},
    {"role_label": "网格员", "name": "孙永林"},
    {"role_label": "网格员", "name": "周玉珍"},
    {"role_label": "网格员", "name": "吴德明"},
    {"role_label": "网格员", "name": "徐淑芳"},
    {"role_label": "民政干事", "name": "马文华"},
    {"role_label": "社工", "name": "朱慧珍"},
    {"role_label": "社工", "name": "胡素芬"},
    {"role_label": "护理员", "name": "郭丽华"},
    {"role_label": "志愿者组长", "name": "何金凤"},
]

# 网格员按楼栋分配（8 个网格员覆盖 33 栋楼）
GRID_WORKER_ASSIGNMENTS = {
    "祥盛家园1号楼": 0, "祥盛家园2号楼": 0, "祥盛家园3号楼": 0, "祥盛家园4号楼": 0,
    "祥盛家园5号楼": 1, "祥盛家园6号楼": 1, "祥盛家园7号楼": 1, "祥盛家园8号楼": 1,
    "祥盛家园9号楼": 2, "祥盛家园10号楼": 2, "祥盛家园11号楼": 2, "祥盛家园12号楼": 2,
    "祥盛家园13号楼": 3, "祥盛家园14号楼": 3, "祥盛家园15号楼": 3,
    "祥盛家园16号楼": 4, "祥盛家园17号楼": 4, "祥盛家园18号楼": 4, "祥盛家园19号楼": 4,
    "南北乐章1号楼": 5, "南北乐章2号楼": 5, "南北乐章3号楼": 5, "南北乐章4号楼": 5,
    "南北乐章5号楼": 6, "南北乐章6号楼": 6, "南北乐章7号楼": 6, "南北乐章8号楼": 6,
    "桂花溪园1号楼": 7, "桂花溪园2号楼": 7, "桂花溪园3号楼": 7,
    "桂花溪园4号楼": 7, "桂花溪园5号楼": 7, "桂花溪园6号楼": 7,
}


def gen_phone():
    prefixes = ["138", "139", "136", "158", "159", "188", "187", "150", "151", "152"]
    return random.choice(prefixes) + "".join([str(random.randint(0, 9)) for _ in range(8)])


def gen_name(idx):
    surname = SURNAMES[idx % len(SURNAMES)]
    pool = GIVEN_NAMES_M if idx % 2 == 0 else GIVEN_NAMES_F
    given = pool[(idx // len(SURNAMES)) % len(pool)]
    return surname + given


def gen_address(area_name, building_num):
    building = f"{area_name}{building_num}号楼"
    unit = random.randint(1, 3)
    floor = random.randint(1, 6)
    room = random.randint(1, 4)
    return f"{building}{unit}单元{floor}0{room}室"


def gen_emergency_contact(elder_name):
    rel = random.choice(["儿子", "女儿", "儿媳", "女婿", "侄子", "侄女"])
    surname = elder_name[0]
    given = random.choice(GIVEN_NAMES_M[:15] + GIVEN_NAMES_F[:15])
    return f"{surname}{given}({rel})", gen_phone()


async def clean_data(db):
    """清除所有社区相关数据（按外键依赖顺序）"""
    print("清除现有数据...")
    await db.execute(text("DELETE FROM risk_score_snapshots"))
    await db.execute(text("DELETE FROM alerts"))
    await db.execute(text("DELETE FROM community_events"))
    await db.execute(text("DELETE FROM canteen_records"))
    await db.execute(text("DELETE FROM alert_rules"))
    await db.execute(text("DELETE FROM community_worker_assignments"))
    await db.execute(text("DELETE FROM community_elders"))
    await db.execute(text("DELETE FROM community_workers"))
    await db.execute(text("DELETE FROM communities"))
    await db.execute(text("DELETE FROM care_relations"))
    await db.execute(text("DELETE FROM view_events"))
    await db.execute(text("DELETE FROM care_moments"))
    await db.execute(text("DELETE FROM users WHERE role IN ('elder', 'worker', 'family')"))
    await db.commit()
    print("数据清除完成")


async def seed(clean=False):
    async with async_session() as db:
        if clean:
            await clean_data(db)

        existing = (await db.execute(
            select(Community).where(Community.name == "溪东社区")
        )).scalar_one_or_none()
        if existing:
            print("溪东社区已存在，跳过（使用 --clean 重新生成）")
            return

        # 创建社区
        community = Community(
            id=uuid.uuid4(),
            name="溪东社区",
            address="杭州余杭区瓶窑镇",
        )
        db.add(community)
        await db.flush()

        # 创建 15 名工作者
        grid_workers = []  # 存 8 个网格员的 worker ID（按 WORKERS 列表中的顺序 index 2-9）
        worker_ids = []
        pw_hash = pwd_ctx.hash("admin123")
        for i, w in enumerate(WORKERS):
            phone = f"1380013{8000 + i:04d}" if i == 0 else gen_phone()
            user = User(
                id=uuid.uuid4(),
                openid=f"worker_{uuid.uuid4().hex[:8]}",
                role="worker",
                nickname=w["name"],
                phone=phone,
            )
            db.add(user)
            await db.flush()

            worker = CommunityWorker(
                id=uuid.uuid4(),
                user_id=user.id,
                community_id=community.id,
                name=w["name"],
                phone=phone,
                role_label=w["role_label"],
                password_hash=pw_hash,
            )
            db.add(worker)
            worker_ids.append(worker.id)

            if w["role_label"] == "网格员":
                grid_workers.append(worker.id)

        await db.flush()
        print(f"创建 {len(WORKERS)} 名工作者")

        # 构建楼栋 → worker ID 映射
        building_worker_map = {}
        for building_key, grid_idx in GRID_WORKER_ASSIGNMENTS.items():
            building_worker_map[building_key] = grid_workers[grid_idx]

        # 生成老人：A=61, B=200, C=1840
        total_elders = sum(a["elders"] for a in AREAS)
        levels = ["A"] * 61 + ["B"] * 200 + ["C"] * (total_elders - 261)
        random.shuffle(levels)

        elder_idx = 0
        used_names = set()
        batch = []

        for area in AREAS:
            elders_per_building = area["elders"] // area["buildings"]
            remainder = area["elders"] % area["buildings"]

            for b in range(1, area["buildings"] + 1):
                count = elders_per_building + (1 if b <= remainder else 0)
                building_name = f"{area['name']}{b}号楼"
                assigned_worker = building_worker_map.get(building_name)

                for _ in range(count):
                    level = levels[elder_idx]
                    name = gen_name(elder_idx)
                    # 去重
                    while name in used_names:
                        name = name + str(random.randint(0, 9))
                    used_names.add(name)

                    notes = random.choice(
                        HEALTH_NOTES_A if level == "A" else
                        HEALTH_NOTES_B if level == "B" else
                        HEALTH_NOTES_C
                    )
                    ec_name, ec_phone = gen_emergency_contact(name)

                    user_id = uuid.uuid4()
                    batch.append({
                        "user": User(
                            id=user_id,
                            openid=f"elder_{uuid.uuid4().hex[:8]}",
                            role="elder",
                            nickname=name,
                            phone=gen_phone(),
                        ),
                        "elder": CommunityElder(
                            id=uuid.uuid4(),
                            community_id=community.id,
                            elder_id=user_id,
                            care_level=level,
                            address=gen_address(area["name"], b),
                            emergency_contact_name=ec_name,
                            emergency_contact_phone=ec_phone,
                            health_notes=notes,
                            assigned_worker_id=assigned_worker,
                        ),
                    })
                    elder_idx += 1

                    if len(batch) >= 200:
                        for item in batch:
                            db.add(item["user"])
                        await db.flush()
                        for item in batch:
                            db.add(item["elder"])
                        await db.flush()
                        batch.clear()

            print(f"  {area['name']}: {area['elders']} 位老人")

        # 处理剩余
        if batch:
            for item in batch:
                db.add(item["user"])
            await db.flush()
            for item in batch:
                db.add(item["elder"])
            await db.flush()
            batch.clear()

        await db.commit()

        a_count = levels[:elder_idx].count("A")
        b_count = levels[:elder_idx].count("B")
        c_count = levels[:elder_idx].count("C")

        print("=" * 50)
        print("溪东社区数据创建完成!")
        print("=" * 50)
        print(f"  社区: 溪东社区 (ID: {community.id})")
        print(f"  工作者: {len(WORKERS)} 人")
        print(f"  老人总计: {elder_idx} 位")
        print(f"    A级(重点关爱): {a_count}")
        print(f"    B级(独居关注): {b_count}")
        print(f"    C级(健康互助): {c_count}")
        print(f"\n  站长登录: 13800138000 / admin123")
        print(f"  所有工作者密码: admin123")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="溪东社区种子数据")
    parser.add_argument("--clean", action="store_true", help="清除现有数据后重新生成")
    args = parser.parse_args()
    asyncio.run(seed(clean=args.clean))
