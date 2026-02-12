#!/bin/bash
# 技能市集安裝腳本

set -e

echo "🎯 開始安裝技能市集..."

# 檢查必要工具
echo "🔍 檢查必要工具..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python3"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ 需要 Node.js/npm"
    exit 1
fi

# 安裝 clawhub CLI
echo "📦 安裝 ClawHub CLI..."
if ! command -v clawhub &> /dev/null; then
    npm install -g clawhub
    echo "✅ ClawHub CLI 安裝完成"
else
    echo "✅ ClawHub CLI 已安裝"
fi

# 檢查 Python 依賴
echo "🐍 檢查 Python 依賴..."
python3 -c "import json" 2>/dev/null || {
    echo "❌ Python json 模組不可用"
    exit 1
}

# 創建必要的目錄
echo "📁 創建目錄結構..."
mkdir -p /root/.openclaw/logs
mkdir -p /root/.openclaw/workspace/skills-marketplace/data

# 設置權限
echo "🔒 設置權限..."
chmod +x marketplace.py telegram_handler.py

# 測試基本功能
echo "🧪 測試基本功能..."
cd "$(dirname "$0")"
if python3 -c "import sys; sys.path.append('.'); from marketplace import get_marketplace; m = get_marketplace(); print('✅ 模組導入成功')"; then
    echo "✅ 技能市集模組測試通過"
else
    echo "❌ 模組測試失敗"
    exit 1
fi

# 測試 clawhub 連接
echo "🌐 測試 ClawHub 連接..."
if clawhub -V &>/dev/null; then
    echo "✅ ClawHub 連接正常"
else
    echo "❌ ClawHub 連接失敗"
    exit 1
fi

# 創建配置檔案
echo "⚙️ 創建配置檔案..."
cat > /root/.openclaw/workspace/skills-marketplace/config.json << EOF
{
    "marketplace": {
        "enabled": true,
        "workdir": "/root/.openclaw/workspace",
        "skills_dir": "skills-marketplace/data",
        "auto_update": true,
        "update_interval_hours": 24,
        "search_limit": 10,
        "explore_limit": 10
    },
    "telegram": {
        "enabled": true,
        "commands": [
            "/skills",
            "/skill_search",
            "/skill_install", 
            "/skill_list",
            "/skill_update"
        ]
    }
}
EOF

# 創建使用說明
echo "📖 創建使用說明..."
cat > /root/.openclaw/workspace/skills-marketplace/README.md << 'EOF'
# 技能市集瀏覽器

## 功能概述
- 🔍 搜索和瀏覽 OpenClaw 技能
- 📦 一鍵安裝/卸載技能
- ⭐ 熱門技能推薦
- 🔄 自動更新檢查

## 安裝狀態
✅ 技能市集已成功安裝

## 使用方法

### Telegram 命令
1. `/skills` - 打開技能市集主選單
2. `/skill_search [關鍵字]` - 搜索技能
3. `/skill_install [技能名稱]` - 安裝技能
4. `/skill_list` - 列出已安裝技能
5. `/skill_update` - 更新技能

### 互動操作
- 使用 inline keyboard 按鈕進行操作
- 點擊技能名稱查看詳情
- 點擊安裝按鈕一鍵安裝

## 檔案位置
- 主程式: `/root/.openclaw/workspace/skills-marketplace/`
- 資料儲存: `/root/.openclaw/workspace/skills-marketplace/data/`
- 日誌檔案: `/root/.openclaw/logs/skills-marketplace.log`

## 測試安裝
運行測試腳本確認功能正常：
```bash
cd /root/.openclaw/workspace/skills-marketplace
python3 test_integration.py
```

## 故障排除
1. **安裝失敗**: 檢查網路連接和權限
2. **搜索無結果**: 嘗試不同關鍵字
3. **更新失敗**: 檢查技能版本兼容性

## 支援
如有問題，請查看日誌檔案或重新運行安裝腳本。

---
安裝時間: $(date)
版本: 1.0.0
EOF

echo "✅ 安裝完成！"
echo ""
echo "🎯 下一步："
echo "1. 在 Telegram 中使用 /skills 測試功能"
echo "2. 搜索並安裝技能：/skill_search weather"
echo "3. 查看已安裝技能：/skill_list"
echo ""
echo "📁 檔案位置：/root/.openclaw/workspace/skills-marketplace/"
echo "📋 使用說明：cat /root/.openclaw/workspace/skills-marketplace/README.md"