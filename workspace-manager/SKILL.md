---
name: workspace-manager
description: 工作空間管理工具 - 完整的檔案瀏覽器、目錄導覽和檔案操作技能
metadata:
  {
    "openclaw":
      {
        "requires": { "python": "3.8+" },
        "telegram": {
          "commands": [
            {
              "command": "workspace",
              "description": "打開工作空間管理選單"
            },
            {
              "command": "ws",
              "description": "工作空間快捷命令"
            },
            {
              "command": "file_browse",
              "description": "瀏覽檔案目錄"
            },
            {
              "command": "file_search",
              "description": "搜尋檔案和內容"
            },
            {
              "command": "file_edit",
              "description": "編輯文字檔案"
            }
          ]
        }
      },
  }
---

# 工作空間管理工具

## 技能信息
- **名稱**：workspace-manager
- **版本**：2.0.0
- **作者**：OpenClaw Team
- **描述**：完整的工作空間管理工具，提供檔案瀏覽、目錄導覽、檔案操作和搜尋功能
- **分類**：workspace, file-management, productivity

## 功能特性

### 📁 檔案瀏覽器
- **樹狀目錄導覽**：直觀的樹狀結構顯示目錄層級
- **檔案預覽**：支援文字檔案、Markdown、程式碼預覽
- **縮圖顯示**：圖片檔案縮圖預覽
- **檔案資訊**：顯示檔案大小、修改時間、權限等資訊

### 🔍 搜尋功能
- **檔案名稱搜尋**：快速搜尋檔案和目錄
- **內容搜尋**：全文搜尋檔案內容
- **進階篩選**：按檔案類型、大小、修改時間篩選
- **搜尋歷史**：保存搜尋記錄

### 📄 檔案操作
- **讀取檔案**：查看檔案內容
- **編輯檔案**：線上文字編輯器
- **刪除檔案**：安全刪除（可恢復）
- **重命名**：檔案和目錄重命名
- **移動/複製**：檔案操作
- **新建檔案/目錄**：快速創建

### 🌳 目錄管理
- **目錄樹狀圖**：視覺化目錄結構
- **目錄統計**：顯示目錄大小、檔案數量
- **批次操作**：批量處理檔案
- **書籤功能**：常用目錄書籤

### 🎨 使用者介面
- **Telegram 互動**：完整的 inline keyboard 介面
- **分頁瀏覽**：支援大型目錄分頁
- **快速操作**：常用操作快捷鍵
- **主題支援**：可切換介面主題

## 安裝要求
- OpenClaw 版本：2026.2.0 或更高
- Python 版本：3.8+
- 依賴套件：見 package.json

## 使用方式

### Telegram 命令
```
/workspace - 打開工作空間管理主選單
/ws - 快捷命令（等同 /workspace）
/file_browse [路徑] - 瀏覽指定目錄
/file_search <關鍵字> - 搜尋檔案
/file_edit <檔案路徑> - 編輯檔案
```

### 互動介面功能
1. **主選單**：提供所有功能的入口
2. **檔案瀏覽器**：樹狀目錄導覽和檔案列表
3. **搜尋介面**：搜尋框和結果列表
4. **編輯器**：文字檔案編輯器
5. **操作選單**：檔案操作選項

## 命令列表

### 主要命令
- `/workspace` - 顯示主選單
- `/workspace browse [路徑]` - 瀏覽指定目錄
- `/workspace search <關鍵字>` - 搜尋檔案
- `/workspace edit <檔案>` - 編輯檔案
- `/workspace new <類型> <名稱>` - 創建新檔案/目錄
- `/workspace stats` - 顯示空間使用統計
- `/workspace tree [深度]` - 顯示目錄樹狀圖

### 快捷命令
- `/ws` - 等同 /workspace
- `/file_browse [路徑]` - 快速瀏覽
- `/file_search <關鍵字>` - 快速搜尋
- `/file_edit <檔案>` - 快速編輯

## 配置選項

在 `openclaw.json` 中添加：

```json
{
  "skills": {
    "workspace-manager": {
      "enabled": true,
      "config": {
        "default_path": "/root/.openclaw/workspace",
        "max_file_size": 10485760,
        "allowed_extensions": [
          ".txt", ".md", ".py", ".js", ".json", ".yaml", ".yml",
          ".html", ".css", ".xml", ".csv", ".log", ".ini", ".cfg"
        ],
        "image_preview": true,
        "backup_enabled": true,
        "backup_dir": "/root/.openclaw/backups",
        "search_history_size": 50,
        "bookmarks": [
          "/root/.openclaw/workspace",
          "/root/.openclaw/logs",
          "/root/.openclaw/config"
        ],
        "theme": "dark",
        "items_per_page": 20
      }
    }
  }
}
```

## 資料儲存

技能資料儲存在工作空間：
```
/root/.openclaw/workspace/workspace-manager/
├── data/
│   ├── bookmarks.json      # 書籤列表
│   ├── search_history.json # 搜尋歷史
│   ├── preferences.json    # 使用者偏好
│   └── trash/              # 回收站（已刪除檔案）
├── cache/
│   ├── thumbnails/         # 縮圖快取
│   └── directory_cache.json # 目錄快取
└── logs/
    └── workspace_manager.log # 操作日誌
```

## 安全限制
- 只能訪問工作空間目錄及其子目錄
- 檔案大小限制：預設 10MB（可配置）
- 禁止執行系統命令
- 操作前自動備份
- 敏感檔案過濾（如 .env, config.json）
- 權限檢查

## 開發者說明

### 技能結構
```
workspace-manager/
├── SKILL.md              # 技能描述文件
├── package.json          # 依賴管理
├── main.py              # 主程式入口
├── config.py            # 配置管理
├── file_browser.py      # 檔案瀏覽器
├── file_editor.py       # 檔案編輯器
├── search_engine.py     # 搜尋引擎
├── telegram_ui.py       # Telegram 介面
├── utils.py             # 工具函數
├── assets/              # 資源檔案
│   ├── icons/           # 圖示
│   └── templates/       # 模板
├── data/                # 資料儲存
└── tests/               # 測試檔案
```

### API 介面
技能提供以下 API 端點：
- `/api/workspace/browse` - 瀏覽目錄
- `/api/workspace/search` - 搜尋檔案
- `/api/workspace/edit` - 編輯檔案
- `/api/workspace/stats` - 獲取統計資訊

## 故障排除

### 常見問題
1. **無法訪問目錄** - 檢查權限設置
2. **檔案太大無法預覽** - 調整 max_file_size 配置
3. **搜尋無結果** - 檢查搜尋路徑和權限
4. **編輯器無法保存** - 檢查檔案權限和磁碟空間

### 日誌位置
```
/root/.openclaw/logs/workspace-manager.log
```

## 版本歷史

### v2.0.0 (2026-02-12) - 完整重構
- 新增樹狀目錄導覽功能
- 增強搜尋引擎（全文搜尋）
- 改進檔案編輯器
- 新增書籤和歷史功能
- 優化 Telegram 互動介面
- 新增縮圖預覽功能

### v1.0.0 (2026-02-11) - 初始版本
- 基本檔案瀏覽功能
- 簡單搜尋功能
- 基礎檔案操作
- Telegram 命令支援