#!/bin/bash
# 安装 EZLove 监控定时任务（在服务器上以 ezlove-deploy 身份执行）
set -e
TARGET="$HOME/ezlove-monitor/crontab.txt"
cat > "$TARGET" <<'EOF'
* * * * * /usr/bin/python3 /home/ezlove-deploy/ezlove-monitor/monitor.py >> /home/ezlove-deploy/ezlove-monitor/monitor.log 2>&1
*/3 * * * * /usr/bin/python3 /home/ezlove-deploy/ezlove-monitor/github-commits.py >> /home/ezlove-deploy/ezlove-monitor/commits.log 2>&1
0 3 * * * /home/ezlove-deploy/bin/cleanup-releases.sh >> /home/ezlove-deploy/logs/release-cleanup.log 2>&1
EOF
crontab "$TARGET"
echo "=== installed crontab ==="
crontab -l