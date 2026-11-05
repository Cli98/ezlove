#!/usr/bin/env python3
"""把 GitHub 提交记录推送到钉钉「GitHub 机器人」（cron 每 3 分钟执行）。

背景：dingtalk_webhook 只能发 text/markdown（自定义机器人），而 GitHub 类型机器人
只接受 GitHub push 报文，普通消息会被拒（errcode=300001）。所以这里主动拉 GitHub
提交，拼成与 GitHub webhook 一致的报文再投递，无需在 GitHub 仓库里配 webhook。

用法：
    python3 github-commits.py           # 正常执行，有新提交就推送
    python3 github-commits.py --test    # 把最新一条提交推一次，用于验证连通性
    python3 github-commits.py --status  # 查看上次检查与已记录的提交
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from monitor import BASE, load_config

STATE_PATH = BASE / "commits-state.json"
API = "https://api.github.com/repos/{repo}/commits?sha={branch}&per_page=15"


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def fetch_commits(repo: str, branch: str) -> tuple[list[dict], str | None]:
    url = API.format(repo=repo, branch=branch)
    req = urllib.request.Request(url, headers={
        "User-Agent": "ezlove-monitor/1.0",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        return [], f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return [], f"{type(exc).__name__}: {exc}"[:120]


def build_payload(repo: str, branch: str, before: str, items: list[dict]) -> dict:
    owner, name = repo.split("/", 1)
    head = items[0]
    commits = [{
        "id": item["sha"],
        "message": item["commit"]["message"],
        "url": item["html_url"],
        "author": {"name": item["commit"]["author"]["name"]},
        "timestamp": item["commit"]["author"]["date"],
        "added": [], "removed": [], "modified": [],
    } for item in items]
    head_commit = commits[0]
    return {
        "ref": f"refs/heads/{branch}",
        "before": before,
        "after": head["sha"],
        "compare": f"https://github.com/{repo}/compare/{before}...{head['sha']}",
        "repository": {
            "full_name": repo,
            "html_url": f"https://github.com/{repo}",
            "name": name,
            "owner": {"name": owner},
        },
        "pusher": {"name": head["commit"]["author"]["name"], "email": "noreply@github.com"},
        "head_commit": head_commit,
        "commits": commits[:10],
    }


def push(webhook: str, payload: dict) -> str | None:
    req = urllib.request.Request(
        webhook, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-GitHub-Event": "push"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read(4096).decode("utf-8") or "{}")
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"[:120]
    if body.get("errcode") not in (0, None):
        return f"errcode={body.get('errcode')} {body.get('errmsg')}"
    return None


def main() -> int:
    cfg = load_config()
    state = load_state()
    webhook = cfg.get("github_webhook") or ""
    repo = cfg.get("github_repo") or ""
    branch = cfg.get("github_branch") or "main"
    interval = int(cfg.get("github_interval_seconds") or 180)
    now = time.time()

    if "--status" in sys.argv:
        last = state.get("last_sha", "")
        checked = state.get("last_check")
        print(f"仓库：{repo} 分支：{branch}")
        print(f"已记录提交：{last[:7] or '无'}")
        print(f"上次检查：{datetime.fromtimestamp(float(checked)):%Y-%m-%d %H:%M:%S}"
              if checked else "上次检查：无")
        return 0

    if not webhook or not repo:
        print("[skip] 未配置 github_webhook / github_repo")
        return 0

    test_mode = "--test" in sys.argv
    if not test_mode and now - float(state.get("last_check", 0)) < interval:
        return 0
    state["last_check"] = now

    items, err = fetch_commits(repo, branch)
    if err:
        save_state(state)
        print(f"[warn] 拉取提交失败：{err}")
        return 0

    if not items:
        save_state(state)
        return 0

    head_sha = items[0]["sha"]
    last_sha = state.get("last_sha") or ""

    if test_mode:
        payload = build_payload(repo, branch, head_sha, items[:1])
        err = push(webhook, payload)
        print(f"[test] {'已推送到群' if not err else '推送失败：' + err}")
        return 0 if not err else 1

    if not last_sha or last_sha == head_sha:
        state["last_sha"] = head_sha
        save_state(state)
        return 0

    new_items = []
    for item in items:
        if item["sha"] == last_sha:
            break
        new_items.append(item)
    if not new_items:
        # last_sha 不在最近 15 条里（强推或积压过多），只报最新一条并重新对齐
        new_items = items[:1]

    err = push(webhook, build_payload(repo, branch, last_sha, new_items))
    if err:
        print(f"[error] 提交推送失败：{err}")
        save_state(state)  # 保留 last_sha，下轮重试
        return 1

    state["last_sha"] = head_sha
    save_state(state)
    print(f"[sent] 已推送 {len(new_items)} 条提交，HEAD={head_sha[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())