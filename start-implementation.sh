#!/bin/bash

# OpenClaw 功能擴展實施啟動腳本
# 2026-02-11

echo "🚀 啟動 OpenClaw 功能擴展實施"
echo "================================"

# 檢查環境
echo "🔍 檢查環境..."
if [ ! -d "/root/.openclaw" ]; then
    echo "❌ OpenClaw 目錄不存在"
    exit 1
fi

if [ ! -f "/root/.openclaw/openclaw.json" ]; then
    echo "❌ OpenClaw 配置檔案不存在"
    exit 1
fi

echo "✅ 環境檢查通過"

# 創建必要的目錄
echo "📁 創建目錄結構..."
mkdir -p /root/.openclaw/workspace/dev-tools
mkdir -p /root/.openclaw/workspace/skill-template
mkdir -p /root/.openclaw/workspace/temp

echo "✅ 目錄創建完成"

# 設置權限
echo "🔒 設置權限..."
chmod +x /root/.openclaw/workspace/dev-tools/*.py 2>/dev/null || true
chmod +x /root/.openclaw/workspace/*.sh 2>/dev/null || true

echo "✅ 權限設置完成"

# 顯示當前狀態
echo ""
echo "📊 當前狀態"
echo "----------"
echo "• 工作空間: /root/.openclaw/workspace"
echo "• 設計文件: 功能擴展設計方案.md"
echo "• 實施計劃: 實施計劃.md"
echo "• 技能模板: skill-template/"
echo "• 開發工具: dev-tools/"

# 顯示下一步行動
echo ""
echo "🎯 下一步行動"
echo "------------"
echo "1. 查看設計方案:"
echo "   cat /root/.openclaw/workspace/功能擴展設計方案.md | head -50"
echo ""
echo "2. 創建第一個技能（技能市集）:"
echo "   cd /root/.openclaw/workspace"
echo "   python dev-tools/skill-builder.py create skills-marketplace"
echo ""
echo "3. 開發技能市集功能:"
echo "   cd /root/.openclaw/workspace/skills-marketplace"
echo "   # 編輯 main.py 實現功能"
echo ""
echo "4. 測試技能:"
echo "   python -m pytest tests/"
echo ""
echo "5. 打包和安裝:"
echo "   python dev-tools/skill-builder.py package skills-marketplace"
echo "   python dev-tools/skill-builder.py install skills-marketplace-*.tar.gz"

# 檢查 Python 環境
echo ""
echo "🐍 Python 環境檢查"
echo "-----------------"
python3 --version
if command -v pip3 &> /dev/null; then
    echo "pip3: 已安裝"
else
    echo "⚠️  pip3 未安裝，建議安裝: apt-get install python3-pip"
fi

# 檢查必要套件
echo ""
echo "📦 檢查必要 Python 套件..."
python3 -c "import requests" 2>/dev/null && echo "✅ requests: 已安裝" || echo "❌ requests: 未安裝"
python3 -c "import psutil" 2>/dev/null && echo "✅ psutil: 已安裝" || echo "❌ psutil: 未安裝"

echo ""
echo "✨ 準備完成！"
echo "開始實施階段一：基礎架構準備"