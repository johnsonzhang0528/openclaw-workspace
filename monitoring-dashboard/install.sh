#!/bin/bash
# 監控儀表板技能安裝腳本

set -e

echo "🚀 開始安裝監控儀表板技能..."

# 檢查是否為 root 用戶
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 請使用 sudo 執行此腳本"
    exit 1
fi

# 檢查 OpenClaw 安裝
if ! command -v openclaw &> /dev/null; then
    echo "❌ 未找到 OpenClaw，請先安裝 OpenClaw"
    exit 1
fi

# 檢查技能目錄
SKILLS_DIR="/usr/lib/node_modules/openclaw/skills"
if [ ! -d "$SKILLS_DIR" ]; then
    echo "❌ OpenClaw 技能目錄不存在: $SKILLS_DIR"
    exit 1
fi

# 獲取當前目錄
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="monitoring-dashboard"

echo "📁 複製技能檔案..."
cp -r "$CURRENT_DIR" "$SKILLS_DIR/"

# 檢查複製是否成功
if [ $? -eq 0 ]; then
    echo "✅ 技能檔案複製成功"
else
    echo "❌ 技能檔案複製失敗"
    exit 1
fi

# 設置檔案權限
echo "🔧 設置檔案權限..."
chmod +x "$SKILLS_DIR/$SKILL_NAME/monitor_bot.py"
chmod +x "$SKILLS_DIR/$SKILL_NAME/telegram_integration.py"
chmod +x "$SKILLS_DIR/$SKILL_NAME/tests/test_monitor.py"

# 檢查 Python 依賴
echo "🐍 檢查 Python 依賴..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，請先安裝 Python 3"
    exit 1
fi

# 檢查必要的 Python 套件
REQUIRED_PACKAGES=("yaml")
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        echo "⚠️  缺少 Python 套件: $package"
        echo "   請執行: pip3 install pyyaml"
    fi
done

# 重啟 OpenClaw
echo "🔄 重啟 OpenClaw 服務..."
if openclaw gateway restart; then
    echo "✅ OpenClaw 重啟成功"
else
    echo "⚠️  OpenClaw 重啟失敗，請手動重啟"
    echo "   執行: openclaw gateway restart"
fi

# 建立符號連結到工作空間（可選）
WORKSPACE_DIR="$HOME/.openclaw/workspace/skills"
if [ -d "$WORKSPACE_DIR" ]; then
    echo "🔗 建立工作空間符號連結..."
    ln -sf "$SKILLS_DIR/$SKILL_NAME" "$WORKSPACE_DIR/$SKILL_NAME"
    echo "✅ 符號連結建立成功"
fi

echo ""
echo "🎉 監控儀表板技能安裝完成！"
echo ""
echo "📋 使用說明："
echo "   1. 在 Telegram 中輸入 /monitor 查看儀表板"
echo "   2. 使用 /monitor detail 查看詳細模式"
echo "   3. 使用 /monitor chart 查看圖表模式"
echo "   4. 使用 /monitor help 查看幫助"
echo ""
echo "🔧 配置檔案位置："
echo "   $SKILLS_DIR/$SKILL_NAME/config/settings.yaml"
echo ""
echo "📝 測試技能："
echo "   cd $SKILLS_DIR/$SKILL_NAME"
echo "   python3 tests/test_monitor.py"
echo ""
echo "🔄 如需更新技能，請重新執行此安裝腳本"
echo "🗑️  如需移除技能，請執行："
echo "   rm -rf $SKILLS_DIR/$SKILL_NAME"
echo "   openclaw gateway restart"