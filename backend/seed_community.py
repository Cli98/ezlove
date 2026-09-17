"""
Seed script: 创建初始社区 + 管理员账号

用法:
  cd backend && PYTHONPATH=. python seed_community.py --password YOUR_PASSWORD

可选参数:
  --phone       管理员手机号 (默认: 13800138000)
  --password    管理员密码 (必填)
  --community   社区名称 (默认: 幸福社区)
"""
import argparse
import asyncio
import uuid
from passlib.context import CryptContext
from app.database import async_session
from app.models.user import User
from app.models.community import Community, CommunityWorker

pwd_ctx = CryptContext(schemes=["bcrypt"])


async def seed(phone: str, password: str, community_name: str):
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(Community))
        if result.scalars().first():
            print("社区已存在，跳过 seed")
            return

        community = Community(
            id=uuid.uuid4(),
            name=community_name,
            address="",
        )
        db.add(community)

        user = User(
            id=uuid.uuid4(),
            openid=f"worker_{uuid.uuid4().hex[:8]}",
            role="worker",
            nickname="管理员",
            phone=phone,
        )
        db.add(user)
        await db.flush()

        worker = CommunityWorker(
            id=uuid.uuid4(),
            user_id=user.id,
            community_id=community.id,
            name="管理员",
            phone=phone,
            role_label="站长",
            password_hash=pwd_ctx.hash(password),
        )
        db.add(worker)

        await db.commit()
        print(f"Seed 完成!")
        print(f"  社区: {community.name} (ID: {community.id})")
        print(f"  手机号: {phone}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="初始化社区数据")
    parser.add_argument("--phone", default="13800138000", help="管理员手机号")
    parser.add_argument("--password", required=True, help="管理员密码")
    parser.add_argument("--community", default="幸福社区", help="社区名称")
    args = parser.parse_args()
    asyncio.run(seed(args.phone, args.password, args.community))
