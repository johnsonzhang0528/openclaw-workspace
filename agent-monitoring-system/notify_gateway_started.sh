#!/bin/bash
# Gateway 啟動完成通知腳本
# 在 Gateway 成功啟動後發送 Telegram 通知

SCRIPT_DIR="/root/.openclaw/workspace/agent-monitoring-system"
PYTHON="/usr/bin/python3"
LOG_FILE="/tmp/gateway_restart_notify.log"

# 記錄執行時間
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ExecStartPost 開始執行" >> "$LOG_FILE"

# 等待 Gateway 真正啟動（最多等待 60 次，每次 1 秒）
for i in {1..60}; do
    status=$(systemctl --user is-active openclaw-gateway 2>&1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 第 $i 次檢查，狀態: $status" >> "$LOG_FILE"
    if [ "$status" = "active" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gateway 已啟動" >> "$LOG_FILE"
        # 發送通知（在背景執行，不阻塞 systemd）
        nohup $PYTHON "$SCRIPT_DIR/send_restart_notification.py" >> "$LOG_FILE" 2>&1 &
        exit 0
    fi
    sleep 1
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gateway 未能在 60 秒內啟動" >> "$LOG_FILE"
exit 0
