#!/bin/bash
# OpenClaw Agent Monitoring System 服務安裝腳本

set -e

echo "🔧 安裝 OpenClaw Agent 監控系統服務"
echo "=========================================="

# 檢查是否為 root 用戶
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 請使用 root 權限執行此腳本"
    echo "   sudo $0"
    exit 1
fi

# 檢查服務檔案是否存在
SERVICE_FILE="openclaw-monitor.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ 找不到服務檔案: $SERVICE_FILE"
    exit 1
fi

# 檢查環境變數檔案
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  找不到環境變數檔案: $ENV_FILE"
    echo "   請先設定 Telegram Bot Token 和 Chat ID"
    echo "   複製 .env.example 為 .env 並編輯設定"
    cp .env.example .env
    echo "✅ 已創建 .env 檔案，請編輯設定後重新執行此腳本"
    exit 1
fi

# 檢查必要配置
echo "🔍 檢查環境配置..."
if grep -q "your_actual_bot_token_here" "$ENV_FILE" || grep -q "dummy_token" "$ENV_FILE"; then
    echo "❌ 請設定真實的 Telegram Bot Token"
    echo "   編輯 $ENV_FILE 檔案，設定 TELEGRAM_BOT_TOKEN"
    exit 1
fi

if grep -q "your_chat_id_here" "$ENV_FILE" || grep -q "dummy_chat_id" "$ENV_FILE"; then
    echo "❌ 請設定真實的 Telegram Chat ID"
    echo "   編輯 $ENV_FILE 檔案，設定 TELEGRAM_CHAT_ID"
    exit 1
fi

echo "✅ 環境配置檢查通過"

# 檢查 Python 依賴
echo "📦 檢查 Python 依賴..."
if python3 -c "import dotenv, requests, sqlite3" 2>/dev/null; then
    echo "✅ Python 依賴已安裝"
else
    echo "⚠️  部分 Python 依賴未安裝"
    echo "   請手動安裝: sudo apt-get install python3-dotenv python3-requests python3-psutil"
    echo "   或使用: pip3 install --user python-dotenv requests psutil"
fi

# 複製服務檔案到 systemd 目錄
echo "📁 安裝 systemd 服務..."
cp "$SERVICE_FILE" /etc/systemd/system/
chmod 644 /etc/systemd/system/"$SERVICE_FILE"

# 重新載入 systemd
systemctl daemon-reload
echo "✅ systemd 服務檔案已安裝"

# 啟用服務
echo "🔗 啟用服務..."
systemctl enable openclaw-monitor.service
echo "✅ 服務已啟用"

# 啟動服務
echo "🚀 啟動服務..."
systemctl start openclaw-monitor.service
echo "✅ 服務已啟動"

# 檢查服務狀態
echo "📊 檢查服務狀態..."
sleep 2
systemctl status openclaw-monitor.service --no-pager

echo ""
echo "=========================================="
echo "🎉 OpenClaw Agent 監控系統安裝完成！"
echo ""
echo "📋 服務管理指令:"
echo "   查看狀態: sudo systemctl status openclaw-monitor"
echo "   查看日誌: sudo journalctl -u openclaw-monitor -f"
echo "   停止服務: sudo systemctl stop openclaw-monitor"
echo "   重啟服務: sudo systemctl restart openclaw-monitor"
echo "   禁用服務: sudo systemctl disable openclaw-monitor"
echo ""
echo "📱 Telegram 通知:"
echo "   請確保 Bot 已加入聊天，並設定正確的 Chat ID"
echo ""
echo "🔧 配置檔案:"
echo "   環境變數: $(pwd)/.env"
echo "   數據庫: $(pwd)/monitoring.db"
echo "=========================================="