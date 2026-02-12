#!/usr/bin/env python3
"""
將效能監控整合到 OpenClaw
"""

import os
import sys
import json
import shutil
from pathlib import Path

def check_dependencies():
    """檢查依賴"""
    try:
        import psutil
        print("✅ psutil 已安裝")
        return True
    except ImportError:
        print("❌ psutil 未安裝")
        print("安裝命令: pip install psutil")
        return False

def create_skill_structure():
    """創建技能結構"""
    workspace = Path("/root/.openclaw/workspace")
    skill_dir = workspace / "performance-monitor-skill"
    
    # 確保目錄存在
    skill_dir.mkdir(exist_ok=True)
    
    # 複製檔案
    files_to_copy = [
        "SKILL.md",
        "performance_monitor.py", 
        "telegram_handler.py"
    ]
    
    for file in files_to_copy:
        src = workspace / "performance-monitor-skill" / file
        if src.exists():
            print(f"✅ {file} 已存在")
        else:
            print(f"❌ {file} 不存在，需要創建")
            
    return skill_dir.exists()

def create_openclaw_handler():
    """創建 OpenClaw 處理器"""
    handler_content = '''#!/usr/bin/env python3
"""
OpenClaw 效能監控處理器
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加技能目錄到路徑
skill_dir = Path("/root/.openclaw/workspace/performance-monitor-skill")
if str(skill_dir) not in sys.path:
    sys.path.insert(0, str(skill_dir))

from telegram_handler import get_handler

logger = logging.getLogger(__name__)

class OpenClawPerformanceHandler:
    """OpenClaw 效能處理器"""
    
    def __init__(self):
        self.handler = get_handler()
        
    async def handle_message(self, message: str) -> str:
        """處理訊息"""
        try:
            # 解析命令
            parts = message.strip().split()
            if not parts:
                return "❓ 請輸入命令"
                
            command = parts[0].lstrip('/')
            args = parts[1:] if len(parts) > 1 else []
            
            # 處理命令
            if command in ["performance", "perf"]:
                return await self.handler.handle_command("performance", args)
            elif command == "help":
                return self.handler.get_help()
            else:
                return f"❓ 未知命令: {command}"
                
        except Exception as e:
            logger.error(f"處理訊息錯誤: {e}")
            return f"❌ 錯誤: {str(e)}"
            
    def get_available_commands(self):
        """獲取可用命令"""
        return {
            "/performance": "顯示系統效能",
            "/performance history": "顯示歷史趨勢",
            "/performance top": "顯示熱門進程",
            "/performance stats": "顯示詳細統計",
            "/performance help": "顯示幫助",
            "/perf": "/performance 的別名"
        }

# 創建全局實例
_handler = None

def get_openclaw_handler():
    """獲取 OpenClaw 處理器"""
    global _handler
    if _handler is None:
        _handler = OpenClawPerformanceHandler()
    return _handler

async def test():
    """測試函數"""
    handler = get_openclaw_handler()
    
    test_messages = [
        "/performance",
        "/performance history",
        "/performance top",
        "/performance stats",
        "/performance help",
        "/perf"
    ]
    
    for msg in test_messages:
        print(f"\\n{'='*50}")
        print(f"測試: {msg}")
        print(f"{'='*50}")
        result = await handler.handle_message(msg)
        print(result)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test())
'''

    handler_path = Path("/root/.openclaw/workspace/performance-monitor-skill/openclaw_handler.py")
    handler_path.write_text(handler_content)
    print(f"✅ 創建 OpenClaw 處理器: {handler_path}")
    
    # 設置執行權限
    handler_path.chmod(0o755)
    
    return handler_path.exists()

def create_install_script():
    """創建安裝腳本"""
    install_content = '''#!/bin/bash
# 效能監控技能安裝腳本

set -e

echo "🔧 安裝效能監控技能..."

# 檢查 Python 依賴
echo "📦 檢查依賴..."
python3 -c "import psutil" 2>/dev/null || {
    echo "安裝 psutil..."
    pip install psutil
}

# 複製技能到系統目錄
SKILL_SRC="/root/.openclaw/workspace/performance-monitor-skill"
SKILL_DEST="/usr/lib/node_modules/openclaw/skills/performance-monitor"

echo "📁 複製技能檔案..."
sudo mkdir -p "$SKILL_DEST"
sudo cp -r "$SKILL_SRC"/* "$SKILL_DEST/"

# 設置權限
sudo chmod -R 755 "$SKILL_DEST"

echo "✅ 技能安裝完成！"
echo ""
echo "📋 下一步："
echo "1. 重啟 OpenClaw: openclaw gateway restart"
echo "2. 在 Telegram 中使用命令: /performance"
echo "3. 查看幫助: /performance help"
'''

    install_path = Path("/root/.openclaw/workspace/install_performance_monitor.sh")
    install_path.write_text(install_content)
    install_path.chmod(0o755)
    
    print(f"✅ 創建安裝腳本: {install_path}")
    return install_path.exists()

def create_usage_examples():
    """創建使用範例"""
    examples = '''# 效能監控技能使用範例

## 基本命令

### 1. 顯示當前效能
```
/performance
```
或
```
/perf
```

### 2. 顯示歷史趨勢
```
/performance history
```

### 3. 顯示熱門進程
```
/performance top
```

### 4. 顯示詳細統計
```
/performance stats
```

### 5. 顯示幫助
```
/performance help
```

## Telegram Inline 按鈕

技能支援以下 inline 按鈕：
- 📊 即時效能
- 📈 歷史趨勢  
- 🔥 熱門進程
- 📋 詳細統計
- 🔄 刷新
- ❓ 幫助

## 數據說明

### CPU 使用率
- 🟢 正常: < 70%
- 🟡 偏高: 70-90%
- 🔴 過高: > 90%

### 記憶體使用率
- 🟢 正常: < 80%
- 🟡 偏高: 80-90%
- 🔴 過高: > 90%

### 系統負載
- 每核心負載 < 1.0: 運行良好
- 每核心負載 1.0-1.5: 正常
- 每核心負載 > 1.5: 需要擴容

## 自動監控

技能會自動：
- 每5秒收集系統數據
- 保留60分鐘歷史數據
- 監控 CPU、記憶體、磁碟、網路
- 識別資源消耗最多的進程

## 故障排除

### 常見問題

1. **"psutil 未安裝" 錯誤**
   ```
   pip install psutil
   ```

2. **"無可用數據" 訊息**
   - 等待5-10秒讓數據收集
   - 檢查監控器是否運行

3. **權限問題**
   - 確保有系統監控權限
   - 以 root 或 sudo 運行

### 日誌位置
- OpenClaw 日誌: `/var/log/openclaw/`
- 技能日誌: 控制台輸出

## 進階配置

### 修改更新間隔
編輯 `performance_monitor.py`：
```python
# 修改 update_interval（秒）
monitor = PerformanceMonitor(update_interval=10)
```

### 修改歷史保留時間
```python
# 修改 history_hours（小時）
monitor = PerformanceMonitor(history_hours=48)
```

### 添加自定義監控
在 `performance_monitor.py` 中添加新的監控函數

## 開發指南

### 檔案結構
```
performance-monitor-skill/
├── SKILL.md              # 技能描述
├── performance_monitor.py # 監控核心
├── telegram_handler.py   # Telegram 介面
├── openclaw_handler.py   # OpenClaw 整合
└── requirements.txt      # 依賴列表
```

### 擴展功能
1. 添加新的監控指標
2. 實現警報系統
3. 添加圖表生成
4. 支援多語言

## 版本資訊
- v1.0.0: 基礎監控功能
- v1.1.0: Telegram 整合
- v1.2.0: Inline 按鈕支援
'''

    examples_path = Path("/root/.openclaw/workspace/performance-monitor-skill/USAGE.md")
    examples_path.write_text(examples)
    
    print(f"✅ 創建使用範例: {examples_path}")
    return examples_path.exists()

def main():
    """主函數"""
    print("🔧 開始整合效能監控技能...")
    print()
    
    # 檢查依賴
    if not check_dependencies():
        print("❌ 依賴檢查失敗")
        return False
        
    # 創建技能結構
    if not create_skill_structure():
        print("❌ 創建技能結構失敗")
        return False
        
    # 創建 OpenClaw 處理器
    if not create_openclaw_handler():
        print("❌ 創建 OpenClaw 處理器失敗")
        return False
        
    # 創建安裝腳本
    if not create_install_script():
        print("❌ 創建安裝腳本失敗")
        return False
        
    # 創建使用範例
    if not create_usage_examples():
        print("❌ 創建使用範例失敗")
        return False
        
    print()
    print("🎉 整合完成！")
    print()
    print("📋 下一步：")
    print("1. 安裝依賴: pip install psutil")
    print("2. 運行安裝腳本: ./install_performance_monitor.sh")
    print("3. 重啟 OpenClaw: openclaw gateway restart")
    print("4. 測試命令: /performance")
    print()
    print("💡 快速測試（無需安裝）:")
    print("  cd /root/.openclaw/workspace/performance-monitor-skill")
    print("  python3 openclaw_handler.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)