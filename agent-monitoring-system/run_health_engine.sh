#!/bin/bash
# 統一監控引擎 cron 排程
# 每分鐘由 crontab 執行，內部 sleep 30 實現 30 秒間隔
# 取代舊的 run_every_30s.sh（雙腳本模式）

cd /root/.openclaw/workspace/agent-monitoring-system

LOG=/tmp/health_engine.log

# D-Bus 環境（cron 環境沒有 session bus）
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"

# 第一次執行
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ── Run 1 ──" >> "$LOG"
/usr/bin/python3 health_engine.py >> "$LOG" 2>&1

# 等待 30 秒後第二次執行
sleep 30

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ── Run 2 ──" >> "$LOG"
/usr/bin/python3 health_engine.py >> "$LOG" 2>&1
