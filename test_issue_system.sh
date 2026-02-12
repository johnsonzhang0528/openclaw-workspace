#!/bin/bash

echo "=== 測試智慧議題追蹤系統 ==="
echo ""

# 檢查 Python 環境
echo "1. 檢查 Python 環境..."
python3 --version
echo ""

# 測試議題管理模組
echo "2. 測試議題管理模組..."
python3 /root/.openclaw/workspace/issue_manager.py
echo ""

# 測試 Telegram 處理器
echo "3. 測試 Telegram 處理器..."
python3 /root/.openclaw/workspace/issue_telegram_handler.py
echo ""

# 測試主要系統
echo "4. 測試主要系統..."
python3 /root/.openclaw/workspace/issue_system_main.py
echo ""

# 檢查檔案結構
echo "5. 檢查檔案結構..."
echo "工作空間目錄:"
ls -la /root/.openclaw/workspace/issues/
echo ""

echo "議題索引:"
cat /root/.openclaw/workspace/issues_index.json | python3 -m json.tool
echo ""

echo "=== 測試完成 ==="