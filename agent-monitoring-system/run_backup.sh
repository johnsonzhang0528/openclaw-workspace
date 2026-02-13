#!/bin/bash
# OpenClaw 排程備份 — 每日 06:00 GMT+8 (= 22:00 UTC 前一天)
# 流程：本地備份 → 驗證 → 遠端推送 → 日誌輪轉
#
# Crontab:
#   0 22 * * * /root/.openclaw/workspace/agent-monitoring-system/run_backup.sh

cd /root/.openclaw/workspace/agent-monitoring-system

LOG=/tmp/backup_engine.log

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ── 排程備份開始 ──" >> "$LOG"
/usr/bin/python3 backup_engine.py full >> "$LOG" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ── 排程備份結束 ──" >> "$LOG"
echo "" >> "$LOG"
