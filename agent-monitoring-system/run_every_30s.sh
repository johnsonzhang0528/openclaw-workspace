#!/bin/bash
# 30 秒間隔執行監控腳本

cd /root/.openclaw/workspace/agent-monitoring-system

# 第一次執行
/usr/bin/python3 unified_dashboard_cron.py >> /tmp/monitoring.log 2>&1

# 等待 30 秒後第二次執行
sleep 30
/usr/bin/python3 unified_dashboard_cron.py >> /tmp/monitoring.log 2>&1
