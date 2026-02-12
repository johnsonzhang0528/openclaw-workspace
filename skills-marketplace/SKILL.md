---
name: skills-marketplace
description: 技能市集瀏覽器 - 瀏覽、搜索、安裝和管理 OpenClaw 技能
metadata:
  {
    "openclaw":
      {
        "requires": { "bins": ["clawhub"] },
        "install":
          [
            {
              "id": "node",
              "kind": "node",
              "package": "clawhub",
              "bins": ["clawhub"],
              "label": "安裝 ClawHub CLI (npm)",
            },
          ],
        "telegram": {
          "commands": [
            {
              "command": "skills",
              "description": "打開技能市集"
            },
            {
              "command": "skill_search",
              "description": "搜索技能"
            },
            {
              "command": "skill_install",
              "description": "安裝技能"
            },
            {
              "command": "skill_list",
              "description": "列出已安裝技能"
            }
          ]
        }
      },
  }
---

# 技能市集瀏覽器

## 功能概述

提供完整的技能市集功能，包括：
- 🔍 技能搜索和瀏覽
- 📦 一鍵安裝/卸載
- ⭐ 熱門技能推薦
- 🔄 自動更新檢查
- 📊 技能評分和評論

## 安裝需求

```bash
npm i -g clawhub
```

## 使用方法

### Telegram 命令
- `/skills` - 打開技能市集主選單
- `/skill_search [關鍵字]` - 搜索技能
- `/skill_install [技能名稱]` - 安裝技能
- `/skill_list` - 列出已安裝技能

### 互動介面
使用 inline keyboard 按鈕進行互動：
- 瀏覽技能列表
- 查看技能詳情
- 安裝/卸載技能
- 評分和評論

## 資料儲存

技能資料儲存在工作空間：
```
/root/.openclaw/workspace/skills-marketplace/
├── installed_skills.json    # 已安裝技能列表
├── catalog_cache.json       # 目錄快取
└── user_preferences.json    # 使用者偏好
```

## 配置選項

在 `openclaw.json` 中添加：

```json
{
  "skills": {
    "marketplace": {
      "enabled": true,
      "catalog_url": "https://clawhub.com/api/skills",
      "auto_update": true,
      "update_interval_hours": 24
    }
  }
}
```

## 開發者說明

### 技能結構
每個技能應包含：
- `SKILL.md` - 技能描述文件
- `package.json` - 依賴管理
- 主程式檔案
- 測試檔案

### 發布技能
```bash
clawhub publish ./my-skill --slug my-skill --name "My Skill" --version 1.0.0
```

## 故障排除

### 常見問題
1. **安裝失敗** - 檢查網路連接和權限
2. **搜索無結果** - 嘗試不同關鍵字
3. **更新失敗** - 檢查技能版本兼容性

### 日誌位置
```
/root/.openclaw/logs/skills-marketplace.log
```

## 版本歷史

- v1.0.0 (2026-02-11) - 初始版本
  - 基本搜索和安裝功能
  - Telegram 互動介面
  - 技能管理功能