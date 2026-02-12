#!/bin/bash
# 每分鐘檢查是否有最近的 Gateway 重啟，如果有則發送通知

SCRIPT_DIR="/root/.openclaw/workspace/agent-monitoring-system"
PYTHON="/usr/bin/python3"

# 直接執行 Python 腳本（它會自動檢查 uptime 和去重）
$PYTHON "$SCRIPT_DIR/send_restart_notification.py"
