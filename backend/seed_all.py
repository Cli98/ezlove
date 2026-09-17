"""
溪东社区完整种子数据：按顺序执行所有 seed 脚本

用法:
  cd backend && PYTHONPATH=. python seed_all.py [--clean]

--clean: 清除所有现有数据后重新生成
"""
import argparse
import asyncio
import sys

from seed_elders import seed as seed_elders
from seed_activity import seed_activity


async def main(clean=False):
    print("=" * 60)
    print("溪东社区完整数据初始化")
    print("=" * 60)

    print("\n[1/2] 创建社区 + 老人 + 工作者...")
    await seed_elders(clean=clean)

    print("\n[2/2] 生成 30 天活动数据...")
    await seed_activity()

    print("\n" + "=" * 60)
    print("全部完成！")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="溪东社区完整种子数据")
    parser.add_argument("--clean", action="store_true", help="清除现有数据后重新生成")
    args = parser.parse_args()
    asyncio.run(main(clean=args.clean))
