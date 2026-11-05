#!/usr/bin/env python3
"""把服务器上的 config.json 升级到最新配置项（保留 webhook 等本机凭证）。

只改阈值、限流开关与探测目标，不动 dingtalk_webhook / log_cmd。
用法（与 monitor.py 同目录）：python3 sync-config.py
"""
from __future__ import annotations

import json
import os
import sys

from monitor import CONFIG_PATH

UPDATES = {
    # 阈值放宽：避免瞬时抖动就告警
    "slow_ms": 5000,
    "error5xx_ratio": 0.2,
    "min_requests": 30,
    "error5xx_count": 5,
    # 三层限流
    "alerts_enabled": True,
    "cooldown_seconds": 900,
    "max_cooldown_seconds": 3600,
    "max_per_hour": 6,
}

# Docker 未把后端 8001 映射到宿主机回环，直接探这个地址永远 Connection refused（会每分钟报严重告警）
BAD_PROBES = {"http://127.0.0.1:8001/health"}
GOOD_INTERNAL = "http://127.0.0.1/ezlove-health"


def main() -> int:
    cfg: dict = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[error] 现有 config.json 读取失败：{exc}")
            return 1
    if not cfg.get("dingtalk_webhook"):
        print("[error] 现有 config.json 缺少 dingtalk_webhook，请先补上再执行")
        return 1

    cfg.update(UPDATES)
    urls = cfg.get("probe_urls") or []
    if any(url in BAD_PROBES for url in urls):
        cfg["probe_urls"] = [GOOD_INTERNAL if url in BAD_PROBES else url for url in urls]
        print("[fix] probe_urls 中的 127.0.0.1:8001 已换成宿主机 nginx 入口")
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(CONFIG_PATH, 0o600)
    except OSError as exc:
        print(f"[error] 写入失败：{exc}")
        return 1

    masked = {k: ("***" if k == "dingtalk_webhook" else v) for k, v in cfg.items()}
    print("已更新 config.json：")
    print(json.dumps(masked, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())