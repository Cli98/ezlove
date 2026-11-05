#!/usr/bin/env python3
"""告警限流逻辑的回归测试（纯断言，无第三方依赖）。

运行：python3 test_limits.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import monitor

NOW = 1_800_000_000.0


def make_cfg(**overrides) -> dict:
    cfg = dict(monitor.DEFAULTS)
    cfg.update(overrides)
    return cfg


def alert(key: str = "health_down") -> dict:
    return {"key": key, "level": "严重", "title": "健康检查异常", "lines": ["- x"]}


def with_pause_path(path: Path):
    """把 PAUSE_PATH 指向临时目录，避免受工作区实际文件影响。"""
    monitor.PAUSE_PATH = path


def test_backoff_doubles_then_caps(tmp: Path) -> None:
    with_pause_path(tmp / "PAUSE")
    cfg = make_cfg()
    state: dict = {}

    # 首次告警立即可发，发送后 streak=1，下一轮冷却即翻倍为 1800s
    pending, blocked = monitor.filter_alerts(state, [alert()], NOW, cfg)
    assert blocked is None and len(pending) == 1, (pending, blocked)
    monitor.mark_sent(state, pending, NOW)
    assert state["streak:health_down"] == 1

    assert monitor.filter_alerts(state, [alert()], NOW + 899, cfg)[0] == [], "首轮冷却 900s 内不应重发"
    assert monitor.filter_alerts(state, [alert()], NOW + 1799, cfg)[0] == [], "第二轮冷却已翻倍为 1800s"

    t2 = NOW + 1801
    pending, _ = monitor.filter_alerts(state, [alert()], t2, cfg)
    assert len(pending) == 1, "1800s 后应可重发"
    monitor.mark_sent(state, pending, t2)
    assert state["streak:health_down"] == 2
    assert monitor.filter_alerts(state, [alert()], t2 + 3599, cfg)[0] == [], "第三轮冷却为 3600s"

    t3 = t2 + 3601
    pending, _ = monitor.filter_alerts(state, [alert()], t3, cfg)
    assert len(pending) == 1
    monitor.mark_sent(state, pending, t3)
    assert state["streak:health_down"] == 3

    # 继续告警时冷却封顶在 max_cooldown_seconds，不无线增长
    t4 = t3 + 3601
    pending, _ = monitor.filter_alerts(state, [alert()], t4, cfg)
    assert len(pending) == 1
    monitor.mark_sent(state, pending, t4)
    assert monitor.filter_alerts(state, [alert()], t4 + 3599, cfg)[0] == []
    assert len(monitor.filter_alerts(state, [alert()], t4 + 3601, cfg)[0]) == 1


def test_hourly_cap(tmp: Path) -> None:
    with_pause_path(tmp / "PAUSE")
    cfg = make_cfg()
    state = {"sent_history": [NOW - i * 60 for i in range(cfg["max_per_hour"])]}
    pending, blocked = monitor.filter_alerts(state, [alert()], NOW, cfg)
    assert pending == []
    assert blocked and blocked.startswith("hourly_cap"), blocked

    # 超过一小时的老记录不占额度
    state["sent_history"] = [NOW - 3601 - i for i in range(cfg["max_per_hour"])]
    pending, blocked = monitor.filter_alerts(state, [alert()], NOW, cfg)
    assert len(pending) == 1 and blocked is None
    assert len(state["sent_history"]) == 0, "过期记录应在过滤时被清理"


def test_switch_and_pause(tmp: Path) -> None:
    pause = tmp / "PAUSE"
    with_pause_path(pause)
    cfg = make_cfg()

    pending, blocked = monitor.filter_alerts({}, [alert()], NOW, make_cfg(alerts_enabled=False))
    assert pending == [] and blocked == "disabled", blocked

    pause.write_text("paused\n", encoding="utf-8")
    pending, blocked = monitor.filter_alerts({}, [alert()], NOW, cfg)
    assert pending == [] and blocked == "paused", blocked


def test_recover_resets_streak(tmp: Path) -> None:
    with_pause_path(tmp / "PAUSE")
    state = {"active:health_down": True, "streak:health_down": 3, "last:health_down": NOW}
    recovered = monitor.collect_recovered(state, [])
    assert recovered == ["health_down"], recovered
    assert state["active:health_down"] is False
    assert state["streak:health_down"] == 0

    # 告警仍在时不重置
    state = {"active:error_5xx": True, "streak:error_5xx": 2}
    assert monitor.collect_recovered(state, [alert("error_5xx")]) == []
    assert state["streak:error_5xx"] == 2


def main() -> int:
    tests = [
        test_backoff_doubles_then_caps,
        test_hourly_cap,
        test_switch_and_pause,
        test_recover_resets_streak,
    ]
    for func in tests:
        with tempfile.TemporaryDirectory() as tmp_dir:
            func(Path(tmp_dir))
        print(f"[ok] {func.__name__}")
    print(f"全部 {len(tests)} 项通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())