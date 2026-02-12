#!/bin/bash
# 每日使用量費用報告 — 21:00 GMT+8 (= 13:00 UTC)
cd /root/.openclaw/workspace/agent-monitoring-system
/usr/bin/python3 usage_cost_report.py >> /tmp/usage_cost_report.log 2>&1
