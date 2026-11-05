#!/usr/bin/env python3
"""EZLove 线上轻量监控探针（cron 每分钟执行）。

做三件事：
  1. 主动探测健康端点，记录状态码与耗时（真实用户体验）
  2. 拉取最近访问日志，统计请求量、5xx 占比、出错路径（服务端视角）
  3. 异常时推送到钉钉机器人，并做三层限流避免刷屏

用法：
    python3 monitor.py              # 正常执行，异常时推送钉钉
    python3 monitor.py --dry-run    # 只打印结果，不推送，用于调试
    python3 monitor.py --pause      # 立即静默全部告警（探测与日志照常记录）
    python3 monitor.py --resume     # 恢复告警推送
    python3 monitor.py --status     # 查看开关、暂停状态、近一小时发送记录

限流三层（任一层都可单独止住推送）：
  1. 总开关：config.json 的 alerts_enabled，或命令行 --pause（落一个 PAUSE 文件）
  2. 小时上限：max_per_hour，任意一小时内最多推送这么多条
  3. 同类退避：cooldown_seconds 起，连续告警逐次翻倍，封顶 max_cooldown_seconds

配置文件 config.json（与本脚本同目录，权限 600）：
    {
      "dingtalk_webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
      "dingtalk_secret": "SECxxx（安全设置选「加签」时填，选关键词则留空）",
      "alerts_enabled": true,
      "probe_urls": ["http://127.0.0.1/ezlove-health", "https://yiguanian.ysgy.org.cn/ezlove-health"],
      "slow_ms": 5000,
      "error5xx_count": 5,
      "error5xx_ratio": 0.2,
      "min_requests": 30,
      "window_seconds": 120,
      "cooldown_seconds": 900,
      "max_cooldown_seconds": 3600,
      "max_per_hour": 6
    }
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE / "config.json"
STATE_PATH = BASE / "state.json"
# 触碰此文件即静默全部告警（探测照常），删除即恢复
PAUSE_PATH = BASE / "PAUSE"

DEFAULTS = {
    "dingtalk_webhook": "",
    # 机器人安全设置为「加签」时填写 SEC 开头的密钥；关键词模式留空
    "dingtalk_secret": "",
    "alerts_enabled": True,
    # 内网走宿主机 nginx（Docker 未把 8001 暴露到宿主机回环，直连会 Connection refused）
    "probe_urls": ["http://127.0.0.1/ezlove-health",
                   "https://yiguanian.ysgy.org.cn/ezlove-health"],
    "slow_ms": 5000,
    "error5xx_count": 5,
    "error5xx_ratio": 0.2,
    "min_requests": 30,
    "window_seconds": 120,
    "cooldown_seconds": 900,
    "max_cooldown_seconds": 3600,
    "max_per_hour": 6,
    # 提交通知走 GitHub 类型机器人（只吃 GitHub push 报文，不能发 text/markdown）
    "github_webhook": "",
    "github_repo": "Cli98/ezlove",
    "github_branch": "main",
    "github_interval_seconds": 180,
    "log_cmd": ["sudo", "-n", "/usr/local/sbin/ezlove-release", "logs"],
}

# nginx combined + X-Forwarded-For：
# 1.2.3.4 - - [05/Nov/2026:03:25:14 +0000] "GET /path HTTP/1.0" 200 5920 "ref" "ua" "ip"
LOG_RE = re.compile(r'\[([^\]]+)\] "([A-Z]+) (\S+) [^"]*" (\d{3}) (\d+)')
TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[warn] config.json 解析失败，使用默认值：{exc}")
    return cfg


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def save_state(state: dict) -> None:
    try:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        print(f"[warn] state 写入失败：{exc}")


def probe(url: str, timeout: float) -> dict:
    """发一次 GET，返回状态码、耗时与错误信息。"""
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ezlove-monitor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(2048)
            code = resp.status
        return {"url": url, "code": code, "ms": int((time.perf_counter() - start) * 1000)}
    except urllib.error.HTTPError as exc:
        return {"url": url, "code": exc.code, "ms": int((time.perf_counter() - start) * 1000)}
    except Exception as exc:  # noqa: BLE001 网络类异常统一处理
        return {"url": url, "code": None, "ms": int((time.perf_counter() - start) * 1000),
                "error": f"{type(exc).__name__}: {exc}"[:120]}


def fetch_logs(cmd: list[str]) -> tuple[list[str], str | None]:
    """通过发布通道白名单命令取最近访问日志，返回行列表与错误。"""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], f"{type(exc).__name__}: {exc}"[:120]
    if proc.returncode != 0:
        return [], (proc.stderr or proc.stdout).strip()[:200]
    return proc.stdout.splitlines(), None


def summarize(lines: list[str], window_seconds: int) -> dict:
    """按时间窗口统计请求量、5xx、慢路径不可得（nginx 未记录 request_time）。"""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    total = 0
    errors5xx = 0
    error_paths: dict[str, int] = {}
    bad_lines = 0

    for line in lines:
        match = LOG_RE.search(line)
        if not match:
            bad_lines += 1
            continue
        ts_raw, _method, path, status, _size = match.groups()
        try:
            ts = datetime.strptime(ts_raw, TIME_FMT)
        except ValueError:
            continue
        if ts < cutoff:
            continue
        total += 1
        if status.startswith("5"):
            errors5xx += 1
            error_paths[path] = error_paths.get(path, 0) + 1

    ratio = (errors5xx / total) if total else 0.0
    top_paths = sorted(error_paths.items(), key=lambda kv: kv[1], reverse=True)[:3]
    return {
        "total": total,
        "errors5xx": errors5xx,
        "ratio": ratio,
        "top_paths": top_paths,
        "bad_lines": bad_lines,
    }


def build_alerts(cfg: dict, probes: list[dict], stats: dict) -> list[dict]:
    alerts = []

    down = [p for p in probes if p["code"] != 200]
    if down:
        alerts.append({
            "key": "health_down",
            "level": "严重",
            "title": "健康检查异常",
            "lines": [f"- `{p['url']}` → HTTP {p['code'] or '无响应'} ({p['ms']}ms)"
                      + (f" {p.get('error', '')}" if p.get("error") else "")
                      for p in down],
        })

    slow = [p for p in probes if p["ms"] >= cfg["slow_ms"]]
    if slow:
        alerts.append({
            "key": "slow_response",
            "level": "警告",
            "title": f"响应变慢（阈值 {cfg['slow_ms']}ms）",
            "lines": [f"- `{p['url']}` 耗时 {p['ms']}ms" for p in slow],
        })

    if (stats["errors5xx"] >= cfg["error5xx_count"]
            and stats["total"] >= cfg["min_requests"]
            and stats["ratio"] >= cfg["error5xx_ratio"]):
        paths = "\n".join(f"  - `{p}` {n} 次" for p, n in stats["top_paths"]) or "  - 无明细"
        alerts.append({
            "key": "error_5xx",
            "level": "警告",
            "title": "5xx 错误升高",
            "lines": [
                f"- 最近 {cfg['window_seconds']} 秒请求 {stats['total']} 次，"
                f"5xx {stats['errors5xx']} 次（{stats['ratio'] * 100:.1f}%）",
                "- 出错路径：",
                paths,
            ],
        })

    return alerts


def filter_alerts(state: dict, alerts: list[dict], now: float, cfg: dict) -> tuple[list[dict], str | None]:
    """按开关、小时上限、指数退避三层过滤，返回可发送的告警与拦截原因。"""
    if not cfg.get("alerts_enabled", True):
        return [], "disabled"
    if PAUSE_PATH.exists():
        return [], "paused"

    history = [t for t in state.get("sent_history", []) if now - float(t) < 3600]
    state["sent_history"] = history
    if len(history) >= cfg["max_per_hour"]:
        return [], f"hourly_cap {len(history)}/{cfg['max_per_hour']}"

    pending = []
    for alert in alerts:
        key = alert["key"]
        streak = int(state.get(f"streak:{key}", 0))
        # 连续告警时冷却翻倍，封顶 max_cooldown_seconds，避免持续性故障刷屏
        cooldown = min(cfg["cooldown_seconds"] * (2 ** streak), cfg["max_cooldown_seconds"])
        if now - float(state.get(f"last:{key}", 0)) >= cooldown:
            pending.append(alert)
    return pending, None


def mark_sent(state: dict, alerts: list[dict], now: float) -> None:
    for alert in alerts:
        key = alert["key"]
        state[f"streak:{key}"] = int(state.get(f"streak:{key}", 0)) + 1
        state[f"last:{key}"] = now
        state[f"active:{key}"] = True
    state.setdefault("sent_history", []).append(now)


def collect_recovered(state: dict, active_alerts: list[dict]) -> list[str]:
    """告警消失时重置退避计数，返回本次恢复的 key。"""
    active_keys = {a["key"] for a in active_alerts}
    recovered = []
    for key in ("health_down", "slow_response", "error_5xx", "monitor_broken"):
        if state.get(f"active:{key}") and key not in active_keys:
            state[f"active:{key}"] = False
            state[f"streak:{key}"] = 0
            recovered.append(key)
    return recovered


def signed_webhook(webhook: str, secret: str) -> str:
    """钉钉「加签」模式：把 timestamp + sign 拼到 webhook 查询串。"""
    if not secret:
        return webhook
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest))
    separator = "&" if "?" in webhook else "?"
    return f"{webhook}{separator}timestamp={timestamp}&sign={sign}"


def send_dingtalk(webhook: str, text: str, secret: str = "") -> str | None:
    payload = json.dumps({
        "msgtype": "markdown",
        "markdown": {"title": "EZLove 线上告警", "text": text},
    }).encode("utf-8")
    req = urllib.request.Request(
        signed_webhook(webhook, secret), data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read(4096).decode("utf-8") or "{}")
        if body.get("errcode") not in (0, None):
            return f"钉钉返回 errcode={body.get('errcode')} {body.get('errmsg')}"
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"[:120]
    return None


def fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def cmd_pause() -> int:
    """打上暂停标记：探测与日志照常执行，但不再推送任何告警。"""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        PAUSE_PATH.write_text(f"paused at {stamp}\n", encoding="utf-8")
    except OSError as exc:
        print(f"[error] 写入 {PAUSE_PATH} 失败：{exc}")
        return 1
    print(f"已暂停全部告警推送（{stamp}）。探测照常记录，恢复：python3 monitor.py --resume")
    return 0


def cmd_resume() -> int:
    if not PAUSE_PATH.exists():
        print("当前未暂停，无需恢复")
        return 0
    try:
        PAUSE_PATH.unlink()
    except OSError as exc:
        print(f"[error] 删除 {PAUSE_PATH} 失败：{exc}")
        return 1
    print("已恢复告警推送")
    return 0


def cmd_status() -> int:
    cfg = load_config()
    state = load_state()
    now = time.time()

    print(f"配置文件：{CONFIG_PATH}")
    enabled = cfg.get("alerts_enabled", True)
    print(f"告警开关：{'开启' if enabled else '关闭（config.json alerts_enabled=false）'}")
    if PAUSE_PATH.exists():
        print(f"暂停标记：已暂停（{fmt_ts(PAUSE_PATH.stat().st_mtime)}）")
    else:
        print("暂停标记：未暂停")
    last_run = state.get("last_run")
    print(f"最近一次探测：{fmt_ts(float(last_run)) if last_run else '尚无记录'}")

    history = [float(t) for t in state.get("sent_history", []) if now - float(t) < 3600]
    print(f"近 1 小时已推送：{len(history)}/{cfg['max_per_hour']}")
    for ts in history:
        print(f"  - {fmt_ts(ts)}")

    for key in ("health_down", "slow_response", "error_5xx", "monitor_broken"):
        if not state.get(f"active:{key}"):
            continue
        streak = int(state.get(f"streak:{key}", 0))
        cooldown = min(cfg["cooldown_seconds"] * (2 ** streak), cfg["max_cooldown_seconds"])
        next_ts = float(state.get(f"last:{key}", 0)) + cooldown
        print(f"进行中 {key}：连续 {streak} 轮，下条最早 {fmt_ts(next_ts)}")
    return 0


def main() -> int:
    for flag, handler in (("--pause", cmd_pause), ("--resume", cmd_resume), ("--status", cmd_status)):
        if flag in sys.argv:
            return handler()

    dry_run = "--dry-run" in sys.argv
    cfg = load_config()
    state = load_state()
    now = time.time()
    state["last_run"] = now

    probes = [probe(url, timeout=8) for url in cfg["probe_urls"]]
    lines, log_error = fetch_logs(cfg["log_cmd"])
    stats = summarize(lines, cfg["window_seconds"])

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] probes="
          + ", ".join(f"{p['code']}/{p['ms']}ms" for p in probes)
          + f" requests={stats['total']} 5xx={stats['errors5xx']}")
    if log_error:
        print(f"[warn] 取日志失败：{log_error}")

    alerts = build_alerts(cfg, probes, stats)
    if log_error:
        alerts.append({
            "key": "monitor_broken",
            "level": "警告",
            "title": "监控自身取日志失败",
            "lines": [f"- 原因：`{log_error}`"],
        })

    # 告警消失即清零退避计数，让下次故障能立刻通知（恢复本身不推送，避免二次打扰）
    recovered = collect_recovered(state, alerts)
    if recovered:
        print(f"[recover] 已恢复：{', '.join(recovered)}")

    if not alerts:
        save_state(state)
        return 0

    pending, blocked = filter_alerts(state, alerts, now, cfg)
    if not pending:
        print(f"[skip] {len(alerts)} 条告警未推送：{blocked or '均在冷却期内'}")
        save_state(state)
        return 0

    body_lines = ["### EZLove 线上告警", f"**时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    for alert in pending:
        body_lines.append(f"**【{alert['level']}】{alert['title']}**")
        body_lines.extend(alert["lines"])
        body_lines.append("")
    body_lines.append(
        f"> 不想再收到：执行 `python3 {Path(__file__).name} --pause` 立即静默（`--resume` 恢复）；"
        f"同类告警已自动退避，1 小时最多 {cfg['max_per_hour']} 条"
    )
    text = "\n".join(body_lines)

    if dry_run:
        print(text)
        print(f"[dry-run] 本次可推送 {len(pending)} 条，未写入状态")
        return 0

    webhook = cfg.get("dingtalk_webhook") or ""
    if not webhook:
        print("[error] 未配置 dingtalk_webhook，告警内容如下：\n" + text)
        return 1

    err = send_dingtalk(webhook, text, cfg.get("dingtalk_secret") or "")
    if err:
        print(f"[error] 推送失败：{err}")
        return 1

    mark_sent(state, pending, now)
    save_state(state)
    print(f"[sent] 已推送 {len(pending)} 条告警：{', '.join(a['key'] for a in pending)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())