#!/usr/bin/env bash
# ============================================================
# EZLove 线上部署脚本（在本机 Git Bash 中执行）
#   全流程：打包 → 上传 → check → deploy → 健康检查
#
# 用法：
#   bash deploy.sh          全流程部署
#   bash deploy.sh --check  打包 + 上传 + 远端 check（不部署）
#   bash deploy.sh --pack   仅本地打包并自检（不联网）
#
# 前置条件：本机已配置免密 SSH（~/.ssh/id_ed25519，可用 SSH_KEY 覆盖）
# ============================================================
set -euo pipefail

SERVER="ezlove-deploy@118.178.169.245"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=15 -i "$SSH_KEY")
STAMP="$(date +%Y%m%d%H%M)"
PKG_LOCAL="ezlove-release.tar"
PKG_REMOTE="ezlove-release-${STAMP}.tar"
HEALTH_URL="https://yiguanian.ysgy.org.cn/ezlove-health"
RELEASE="sudo -n /usr/local/sbin/ezlove-release"

MODE="${1:-}"
case "$MODE" in
  ""|--pack|--check) ;;
  *) echo "用法: bash deploy.sh [--pack|--check]"; exit 2 ;;
esac

cd "$(dirname "$0")"

# ---------- 1. 打包 ----------
echo "[1/6] pack: 打包 backend/ + admin-frontend/ ..."
tar --exclude='.env*' --exclude='node_modules' --exclude='__pycache__' \
    --exclude='.git' --exclude='.venv' --exclude='static/uploads' \
    -cf "$PKG_LOCAL" backend admin-frontend
echo "      size: $(du -h "$PKG_LOCAL" | cut -f1)"

# ---------- 2. 自检 ----------
echo "[2/6] self-check: 禁止路径 / 符号链接检查 ..."
if tar -tf "$PKG_LOCAL" | grep -E '(^|/)\.env|(^|/)node_modules(/|$)|(^|/)__pycache__(/|$)|(^|/)\.venv(/|$)|static/uploads'; then
  echo "ERROR: 包内含禁止路径，已终止"
  exit 1
fi
if tar -tvf "$PKG_LOCAL" | grep -E '^[lh]'; then
  echo "ERROR: 包内含符号链接，已终止"
  exit 1
fi
grep -q 'mirrors.aliyun.com/pypi' backend/requirements.txt || echo "      WARN: requirements.txt 未见阿里云 PyPI 镜像源声明（构建可能超时）"
grep -q 'registry.npmmirror.com' admin-frontend/.npmrc 2>/dev/null || echo "      WARN: .npmrc 未见 npmmirror 源声明（构建可能超时）"

if [ "$MODE" = "--pack" ]; then
  echo "done: 仅打包完成（未联网）。"
  exit 0
fi

# ---------- 3. 上传 ----------
echo "[3/6] upload: scp -> uploads/${PKG_REMOTE} ..."
scp "${SSH_OPTS[@]}" "$PKG_LOCAL" "${SERVER}:uploads/${PKG_REMOTE}"

# ---------- 4. 远端 check ----------
echo "[4/6] remote check ..."
ssh "${SSH_OPTS[@]}" "$SERVER" "${RELEASE} check < ~/uploads/${PKG_REMOTE}"

if [ "$MODE" = "--check" ]; then
  echo "done: check 通过（未部署）。正式部署执行: bash deploy.sh"
  exit 0
fi

# ---------- 5. 部署 ----------
echo "[5/6] remote deploy: 构建镜像 + 备份 PG + 更新容器（约几分钟）..."
ssh "${SSH_OPTS[@]}" "$SERVER" "${RELEASE} deploy < ~/uploads/${PKG_REMOTE}"

# ---------- 6. 健康检查 ----------
echo "[6/6] health check ..."
CODE="$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL")"
echo "      ${HEALTH_URL} -> HTTP ${CODE}"
if [ "$CODE" != "200" ]; then
  echo "WARN: 健康检查非 200，可用以下命令排查日志："
  echo "      ssh -i $SSH_KEY $SERVER \"${RELEASE} logs\""
  exit 1
fi

echo "OK: 部署完成。"