#!/usr/bin/env bash
# ============================================================
# EZLove 部署包清理脚本
#   保留最近 N 个 ezlove-release-*.tar，删除更早的，防止服务器磁盘被历史包占满。
#
# 用法：
#   bash cleanup-releases.sh              # 保留最近 5 个（默认）
#   bash cleanup-releases.sh -k 3         # 保留最近 3 个
#   bash cleanup-releases.sh --dry-run    # 只列出将删除的文件，不实际删除
#   bash cleanup-releases.sh --dir /path  # 指定目录（本地测试用）
#
# 服务器定时任务（由安装命令写入 crontab，每天 03:00 执行）：
#   0 3 * * * /home/ezlove-deploy/bin/cleanup-releases.sh >> /home/ezlove-deploy/logs/release-cleanup.log 2>&1
# ============================================================
set -euo pipefail

DIR="$HOME/uploads"
KEEP=5
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -k|--keep) KEEP="${2:?缺少参数}"; shift 2 ;;
    --dir) DIR="${2:?缺少参数}"; shift 2 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "未知参数: $1"; exit 2 ;;
  esac
done

[[ "$KEEP" =~ ^[0-9]+$ ]] || { echo "KEEP 必须是非负整数"; exit 2; }

STAMP="$(date '+%Y-%m-%d %H:%M:%S')"

if [[ ! -d "$DIR" ]]; then
  echo "[$STAMP] 目录不存在，跳过: $DIR"
  exit 0
fi

# 只匹配本项目部署包命名（普通文件），避免误删其它内容；按修改时间倒序
mapfile -t FILES < <(
  find "$DIR" -maxdepth 1 -type f -name 'ezlove-release-[0-9]*.tar' \
    -printf '%T@ %p\n' | sort -rn | awk '{ $1=""; sub(/^ /,""); print }'
)

TOTAL=${#FILES[@]}
if (( TOTAL <= KEEP )); then
  echo "[$STAMP] 共 $TOTAL 个部署包，未超过保留数 $KEEP，无需清理（$DIR）"
  exit 0
fi

DELETE=("${FILES[@]:KEEP}")
echo "[$STAMP] 共 $TOTAL 个部署包，保留最近 $KEEP 个，清理 ${#DELETE[@]} 个（$DIR）"

for f in "${DELETE[@]}"; do
  if (( DRY_RUN )); then
    echo "[$STAMP] [dry-run] 将删除: $f ($(du -h "$f" | cut -f1))"
  else
    rm -f -- "$f"
    echo "[$STAMP] 已删除: $f"
  fi
done

if (( ! DRY_RUN )); then
  echo "[$STAMP] 清理完成，剩余 $KEEP 个部署包"
fi

