#!/bin/bash
# 監控系統定期清理腳本
# 自動清理超過24小時的會話檔案

CLEANUP_DIR="/root/.openclaw/agents/main/sessions"
LOG_FILE="/root/.openclaw/workspace/cleanup.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - 開始清理會話檔案" >> "$LOG_FILE"

# 清理超過24小時的會話檔案
OLD_FILES=$(find "$CLEANUP_DIR" -name "*.jsonl" -type f -mmin +1440 | wc -l)

if [ "$OLD_FILES" -gt 0 ]; then
    echo "找到 $OLD_FILES 個超過24小時的會話檔案" >> "$LOG_FILE"
    
    # 實際清理
    find "$CLEANUP_DIR" -name "*.jsonl" -type f -mmin +1440 -delete
    
    echo "已清理 $OLD_FILES 個舊會話檔案" >> "$LOG_FILE"
else
    echo "沒有需要清理的舊會話檔案" >> "$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - 清理完成" >> "$LOG_FILE"
