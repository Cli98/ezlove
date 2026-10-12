"""统一时间口径工具：全库唯一的"今日零点 / 窗口起点"来源。

全部函数返回 naive 本地 datetime（无 tzinfo），与 DB 列
（TIMESTAMP WITHOUT TIME ZONE）的字面值直比语义一致，
"今日" = 本地自然日（P3 §3.3 契约）。
"""

from datetime import datetime, date, timedelta


def today_start(ref: datetime | None = None) -> datetime:
    """今日零点（naive 本地）。

    ref 缺省取当前时刻；传入固定时刻供测试。
    示例：today_start() → datetime(2026, 9, 16, 0, 0, 0)（本地时区当日）
    """
    base = ref or datetime.now()
    return base.replace(hour=0, minute=0, second=0, microsecond=0)


def window_start(days: int, ref: datetime | None = None) -> datetime:
    """近 days 日（含今日）窗口起点零点 = ref-(days-1) 天的零点。

    days=7 覆盖 activity 日历 / 周趋势；days 参数与 elders.py
    的 days 查询参数同名同义。
    示例：window_start(7) → 9 月 10 日 00:00（当 9 月 16 日调用）
    """
    base = ref or datetime.now()
    start_day = base.date() - timedelta(days=days - 1)
    return day_floor(start_day)


def day_floor(d: date) -> datetime:
    """任意 date 的当日零点 datetime。

    供 export 近 N 日循环的 day 边界构造。
    示例：day_floor(date(2026, 9, 16)) → datetime(2026, 9, 16, 0, 0, 0)
    """
    return datetime(d.year, d.month, d.day)
