#!/usr/bin/env python
"""家属侧未读告警 dry-run 观测脚本（P3 §4.2 上线预案步骤② 的执行体）。

两种模式：
1. 落表模式（默认）：真实触发一次 check_unread_alerts（INSERT alerts 表、不发通知），
   输出新增 unread 告警数 N 与 timed_out 存量数，供按 P3 §3.5 预设规则拍板。
   自校验：要求 ALERT_NOTIFY_ENABLED=false（dry-run 窗口期防误发通知），否则拒绝执行。
2. --readonly 只读统计模式：不落表、不发通知，输出 COLD_START 阶梯各档位预估量。
   豁免 ALERT_NOTIFY_ENABLED 自校验（只读统计安全性自足；两个设计用途——进档预估与
   量级复查——均发生于 ALERT_NOTIFY_ENABLED=true 正式运行期）。

口径澄清（P3-iter3 评分门指令，随方案过门一并落实）：
- 已释放 cohort 的告警在 24h 去重窗口过期后每 24h 例行再告警属预期行为——
  P2 F8-a「24h 后仍未读才收到」正是依赖此机制保障补提醒持续到达，因此
  「存量例行再告警数」是参考值而非噪声；
- COLD_START 阶梯的进档门槛（预估 ≤200 再进档）以「新释放 cohort 关系数」为准
  （= 该档候选集 − 上一档候选集；每关系每 24h 至多 1 条）；
- 落表模式 N 的取数口径 = 脚本执行前后 alerts 表（alert_type='unread'）count 差值，
  与 --readonly 的候选集预估显式对齐（同一判定链 alert_checker._iter_unread_alert_candidates）。

用法（在 backend/ 目录下）：
    python scripts/dry_run_family_check.py             # 落表模式（dry-run 窗口期）
    python scripts/dry_run_family_check.py --readonly  # 只读统计（进档预估 / 量级复查）
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 允许以 `python scripts/dry_run_family_check.py` 直接运行：把 backend/ 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import async_session  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.tasks.alert_checker import (  # noqa: E402
    check_unread_alerts,
    _iter_unread_alert_candidates,
)

# COLD_START 递增阶梯档位（P3 §4.2 步骤 4 分支②）：48→96→168→0 逐档放开，
# 每档观察一轮、档距不小于 24h；每进一档仅新释放一个更早 cohort
COLD_START_LADDER = [48, 96, 168, 0]

# R3 预设阈值：单档新释放 cohort 关系数超过该值时不直接放开，按阶梯分批（P3 §3.5）
R3_THRESHOLD = 200
# R9 预设阈值：timed_out 存量超过该值时建议启用回看窗口限制（P3 §3.5）
R9_THRESHOLD = 500


async def _count_unread_alerts(db) -> int:
    """alerts 表 unread 类型告警总数（落表模式 N 的差值取数基准）。"""
    result = await db.execute(
        select(func.count(Alert.id)).where(Alert.alert_type == "unread")
    )
    return result.scalar() or 0


async def _count_timed_out(db) -> int:
    """timed_out 存量：未解决 urgent 且 response_deadline 已过期（跨社区全量）。"""
    result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.is_resolved == False,
            Alert.alert_level == "urgent",
            Alert.response_deadline.isnot(None),
            Alert.response_deadline < datetime.now(),
        )
    )
    return result.scalar() or 0


async def run_write_mode() -> None:
    # 自校验（仅约束落表模式）：通知开关未关闭时拒绝执行，防落表触发真实通知
    if settings.ALERT_NOTIFY_ENABLED:
        print("拒绝执行：落表模式要求 ALERT_NOTIFY_ENABLED=false（当前为 true）。")
        print("请先在 .env 设置 ALERT_NOTIFY_ENABLED=false 并重启服务，或改用 --readonly 只读统计模式。")
        sys.exit(1)
    if settings.SCHEDULER_ENABLED:
        # 方案仅强制校验通知开关；此处不阻断，但提示并发计数风险
        print("提示：当前 SCHEDULER_ENABLED=true，调度器可能并发产生 unread 告警，使 N 的")
        print("      count 差值混入调度新增量——建议 dry-run 窗口期同时设置 SCHEDULER_ENABLED=false。")

    async with async_session() as db:
        before = await _count_unread_alerts(db)
    # check_unread_alerts 内部自开 session 提交；只落表，通知已被 ALERT_NOTIFY_ENABLED=false 静默
    await check_unread_alerts()
    async with async_session() as db:
        after = await _count_unread_alerts(db)
        timed_out = await _count_timed_out(db)

    n = after - before
    print(f"N（新增 unread 告警数）= {n}")
    print(f"  取数口径：脚本执行前后 alerts 表（alert_type='unread'）count 差值"
          f"（{after} - {before}），")
    print("  与 --readonly 候选集预估共用同一判定链（alert_checker._iter_unread_alert_candidates）。")
    print(f"timed_out 存量数 = {timed_out}")
    print()
    print("预设规则提示（P3 §3.5，N 与 timed_out 实测值回填发布检查单后拍板）：")
    if n <= R3_THRESHOLD:
        print(f"  N ≤ {R3_THRESHOLD}：直接放开（SCHEDULER_ENABLED=true、ALERT_NOTIFY_ENABLED=true、")
        print("  ALERT_COLD_START_UNREAD_HOURS=0）；落表行被 24h 去重窗口吸收，子女上线当天不收通知。")
    else:
        print(f"  N > {R3_THRESHOLD}：设 ALERT_COLD_START_UNREAD_HOURS=48 后启用调度；更早存量按")
        print("  COLD_START 阶梯 48→96→168→0 逐档放开，每档先以 --readonly 预估")
        print(f"  （新释放 cohort 关系数 ≤ {R3_THRESHOLD} 再进档，否则延长当前档观察期）。")
    if timed_out > R9_THRESHOLD:
        print(f"  timed_out > {R9_THRESHOLD}：建议设 WORKSTATION_TIMED_OUT_LOOKBACK_HOURS=72 限制回看窗口。")
    else:
        print(f"  timed_out ≤ {R9_THRESHOLD}：接受一次性真实展示（纯聚合查询、无新通知）。")


async def run_readonly_mode() -> None:
    """只读统计：不落表、不发通知（候选集判定链只做查询，调用方仅计数）。"""
    async with async_session() as db:
        current_h = settings.ALERT_COLD_START_UNREAD_HOURS
        current_candidates = await _iter_unread_alert_candidates(db, current_h)
        print(f"当前配置 ALERT_COLD_START_UNREAD_HOURS={current_h}：候选关系数 = {len(current_candidates)}")
        print()
        print("COLD_START 阶梯各档预估（判定链与正式调度共用 _iter_unread_alert_candidates）：")
        print("  口径：新释放 cohort 关系数 = 该档候选 − 上一档候选（进档门槛以此为准）；")
        print("        存量例行再告警数 = 该档候选 ∩ 上一档候选（参考值——已释放 cohort 每 24h")
        print("        例行再告警属预期，F8-a 补提醒依赖此机制）。")
        prev_ids = None
        for h in COLD_START_LADDER:
            candidates = await _iter_unread_alert_candidates(db, h)
            ids = {rel.id for rel, _, _ in candidates}
            if prev_ids is None:
                # 首档 48h：此前未启用调度，全部为首次释放，无已释放存量
                new_release = len(ids)
                routine = 0
            else:
                new_release = len(ids - prev_ids)
                routine = len(ids & prev_ids)
            print(f"  档位 {h:>3}h：新释放 cohort 关系数 = {new_release}"
                  f"（进档门槛以此为准，≤{R3_THRESHOLD}）"
                  f"｜存量例行再告警数 = {routine}（参考值）")
            prev_ids = ids
        timed_out = await _count_timed_out(db)
    print()
    print(f"timed_out 存量数 = {timed_out}"
          f"（≤{R9_THRESHOLD} 可接受展示跳变；> {R9_THRESHOLD} 建议设 WORKSTATION_TIMED_OUT_LOOKBACK_HOURS=72）")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="家属侧未读告警 dry-run 观测脚本（P3 §4.2 上线预案）"
    )
    parser.add_argument(
        "--readonly", action="store_true",
        help="只读统计模式：不落 alerts 表、不发通知，输出 COLD_START 各档预估量",
    )
    args = parser.parse_args()

    if args.readonly:
        asyncio.run(run_readonly_mode())
    else:
        asyncio.run(run_write_mode())


if __name__ == "__main__":
    main()
