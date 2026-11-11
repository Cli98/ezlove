#!/usr/bin/env python
"""把存量「红外短时静止」规则对齐 12 小时无活动口径（2026-11-11 森滔确认）。

背景：告警规则配置存在 alert_rules 表里，seed 只补缺失、不覆盖已有行，
所以只改代码里的默认值，对已经建过规则的社区不起作用。本脚本负责更新存量行。

改什么（只动 rule_type='stillness'，其它规则一律不碰）：
    enabled          → False   短时静止并入「12 小时无活动提醒」，默认关闭
    threshold_hours  → 12      阈值对齐新口径，以后手动开启也不会退回 1 小时
    config.dedupe_hours → 12   重复间隔同步对齐

脚本幂等，可重复执行；默认只预览不写库，确认无误后加 --apply。
发布通道不执行数据库迁移，线上请用本脚本完成这次数据更新。

用法（在 backend/ 目录或容器内）：
    python scripts/update_stillness_rule.py            # 预览：列出将要改的规则
    python scripts/update_stillness_rule.py --apply    # 实际写入并提交
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 允许以 `python scripts/update_stillness_rule.py` 直接运行：把 backend/ 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import async_session, engine  # noqa: E402
from app.models.alert_rule import AlertRule  # noqa: E402
from app.models.community import Community  # noqa: E402

RULE_TYPE = "stillness"
TARGET_THRESHOLD_HOURS = 12
TARGET_DEDUPE_HOURS = 12


def _needs_update(rule: AlertRule) -> bool:
    """已经是新口径的行跳过，保证脚本可重复执行。"""
    cfg = dict(rule.config or {})
    return not (
        rule.enabled is False
        and rule.threshold_hours == TARGET_THRESHOLD_HOURS
        and cfg.get("dedupe_hours") == TARGET_DEDUPE_HOURS
    )


def _describe(rule: AlertRule, community_name: str) -> str:
    cfg = dict(rule.config or {})
    return (
        f"{community_name} / {rule.care_level} 类："
        f"阈值 {rule.threshold_hours}h → {TARGET_THRESHOLD_HOURS}h，"
        f"重复 {cfg.get('dedupe_hours', '默认')}h → {TARGET_DEDUPE_HOURS}h，"
        f"启用 {'是' if rule.enabled else '否'} → 否"
    )


async def run(apply: bool) -> int:
    # DEBUG=true 时引擎会打印每条 SQL，脚本只需要结果摘要
    engine.echo = False
    async with async_session() as db:
        rows = (
            await db.execute(
                select(AlertRule, Community.name)
                .join(Community, Community.id == AlertRule.community_id)
                .where(AlertRule.rule_type == RULE_TYPE)
                .order_by(Community.name, AlertRule.care_level)
            )
        ).all()

        if not rows:
            print(
                f"未找到 rule_type={RULE_TYPE} 的规则，无需更新"
                "（新社区由代码默认值直接接管）。"
            )
            return 0

        pending = 0
        skipped = 0
        for rule, community_name in rows:
            if not _needs_update(rule):
                skipped += 1
                print(f"[跳过] {community_name} / {rule.care_level} 类已是新口径")
                continue

            pending += 1
            print(f"[{'更新' if apply else '待更新'}] {_describe(rule, community_name)}")
            if apply:
                cfg = dict(rule.config or {})
                cfg["dedupe_hours"] = TARGET_DEDUPE_HOURS
                rule.config = cfg
                rule.threshold_hours = TARGET_THRESHOLD_HOURS
                rule.enabled = False

        if apply:
            await db.commit()
            print(f"\n完成：更新 {pending} 条，跳过 {skipped} 条。")
        else:
            await db.rollback()
            print(f"\n预览模式：待更新 {pending} 条，跳过 {skipped} 条。")
            if pending:
                print("确认无误后加 --apply 执行。")
        return pending


def main() -> None:
    parser = argparse.ArgumentParser(
        description="把存量「红外短时静止」规则对齐 12 小时无活动口径"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际写入数据库（默认只预览，不修改任何数据）",
    )
    args = parser.parse_args()
    asyncio.run(run(args.apply))


if __name__ == "__main__":
    main()