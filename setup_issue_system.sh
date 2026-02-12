#!/bin/bash

echo "=== 智慧議題追蹤系統安裝與設定 ==="
echo ""

# 檢查工作空間
echo "1. 檢查工作空間..."
WORKSPACE="/root/.openclaw/workspace"
if [ ! -d "$WORKSPACE" ]; then
    echo "❌ 工作空間不存在: $WORKSPACE"
    exit 1
fi
echo "✓ 工作空間: $WORKSPACE"
echo ""

# 檢查 Python
echo "2. 檢查 Python 環境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安裝"
    exit 1
fi
python3 --version
echo ""

# 建立必要目錄
echo "3. 建立系統目錄..."
mkdir -p "$WORKSPACE/issues"
echo "✓ 建立 issues/ 目錄"
echo ""

# 檢查現有檔案
echo "4. 檢查現有檔案..."
if [ -f "$WORKSPACE/issues_index.json" ]; then
    echo "✓ issues_index.json 已存在"
else
    echo "⚠ issues_index.json 不存在，將建立新檔案"
fi

if [ -f "$WORKSPACE/system_state.json" ]; then
    echo "✓ system_state.json 已存在"
else
    echo "⚠ system_state.json 不存在，將建立新檔案"
fi
echo ""

# 測試系統
echo "5. 測試系統功能..."
cd "$WORKSPACE"
if python3 issue_integration.py > /dev/null 2>&1; then
    echo "✓ 系統測試通過"
else
    echo "❌ 系統測試失敗"
    echo "詳細錯誤："
    python3 issue_integration.py
    exit 1
fi
echo ""

# 顯示系統狀態
echo "6. 系統狀態："
python3 -c "
import sys
sys.path.append('/root/.openclaw/workspace')
try:
    from issue_system_main import get_issue_system
    system = get_issue_system()
    status = system.get_system_status()
    print(f'總議題數: {status[\"total_issues\"]}')
    print(f'開啟議題: {status[\"open_issues\"]}')
    print(f'已關閉議題: {status[\"closed_issues\"]}')
    print(f'自動偵測: {\"啟用\" if status[\"auto_detection\"] else \"停用\"}')
except Exception as e:
    print(f'錯誤: {e}')
"
echo ""

# 設定檔說明
echo "7. 設定檔位置："
echo "   - 議題索引: $WORKSPACE/issues_index.json"
echo "   - 系統狀態: $WORKSPACE/system_state.json"
echo "   - 議題資料: $WORKSPACE/issues/"
echo ""

# 使用說明
echo "8. 使用指令："
echo "   - /issue        # 查看當前議題列表"
echo "   - /issueHistory # 查看歷史議題"
echo "   - 直接對話      # 自動偵測新議題"
echo ""

echo "=== 安裝完成 ==="
echo ""
echo "系統已準備就緒！開始使用智慧議題追蹤系統吧！"
echo ""
echo "提示："
echo "1. 首次使用建議先執行 /issue 查看空列表"
echo "2. 開始對話，系統會自動偵測新議題"
echo "3. 使用 inline keyboard 按鈕進行互動操作"