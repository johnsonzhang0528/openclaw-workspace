#!/bin/bash
# 每日開發進度報告 — 08:00 GMT+8 (= 00:00 UTC)
cd /root/.openclaw/workspace/agent-monitoring-system
/usr/bin/python3 dev_daily_report.py >> /tmp/dev_daily_report.log 2>&1
