# 技能市集整合指南

## 概述

技能市集瀏覽器已成功開發並測試完成。這個功能允許使用者在 Telegram 中瀏覽、搜索、安裝和管理 OpenClaw 技能。

## 功能特性

### ✅ 已完成功能
1. **技能搜索** - 使用關鍵字搜索技能
2. **最新技能瀏覽** - 查看最新上架的技能
3. **技能安裝** - 一鍵安裝技能
4. **已安裝管理** - 查看和管理已安裝技能
5. **Telegram 介面** - 完整的互動式介面
6. **Inline Keyboard** - 按鈕式操作介面
7. **錯誤處理** - 完整的錯誤處理和提示

### 📱 Telegram 命令
- `/skills` - 打開技能市集主選單
- `/skill_search [關鍵字]` - 搜索技能
- `/skill_install [技能名稱]` - 安裝技能
- `/skill_list` - 列出已安裝技能
- `/skill_update` - 更新技能

## 技術架構

### 檔案結構
```
skills-marketplace/
├── SKILL.md                    # 技能描述文件
├── marketplace.py              # 核心邏輯
├── telegram_handler.py         # Telegram 介面
├── test_integration.py         # 整合測試
├── demo_telegram.py            # 演示腳本
├── install.sh                  # 安裝腳本
├── INTEGRATION.md              # 整合指南 (本文件)
├── README.md                   # 使用說明
└── data/                       # 資料儲存
    ├── installed_skills.json   # 已安裝技能列表
    ├── catalog_cache.json      # 目錄快取
    └── user_preferences.json   # 使用者偏好
```

### 依賴關係
1. **ClawHub CLI** (`npm i -g clawhub`) - 技能管理工具
2. **Python 3.8+** - 執行環境
3. **OpenClaw 系統** - 整合平台

## 安裝步驟

### 自動安裝
```bash
cd /root/.openclaw/workspace/skills-marketplace
./install.sh
```

### 手動安裝
1. 安裝 ClawHub CLI:
   ```bash
   npm i -g clawhub
   ```

2. 創建目錄結構:
   ```bash
   mkdir -p /root/.openclaw/logs
   mkdir -p /root/.openclaw/workspace/skills-marketplace/data
   ```

3. 設置權限:
   ```bash
   chmod +x marketplace.py telegram_handler.py
   ```

4. 測試安裝:
   ```bash
   python3 test_integration.py
   ```

## 整合到 OpenClaw

### 方法一：作為獨立技能
將整個 `skills-marketplace` 目錄複製到 OpenClaw 技能目錄：
```bash
cp -r skills-marketplace /usr/lib/node_modules/openclaw/skills/
```

### 方法二：作為工作空間技能
在 OpenClaw 配置中引用工作空間中的技能：
```json
{
  "skills": {
    "paths": [
      "/root/.openclaw/workspace/skills-marketplace"
    ]
  }
}
```

### 方法三：Telegram 命令註冊
在 OpenClaw 的 Telegram 插件配置中添加命令：
```json
{
  "plugins": {
    "telegram": {
      "commands": {
        "skills": {
          "description": "打開技能市集",
          "handler": "skills-marketplace"
        }
      }
    }
  }
}
```

## 使用範例

### 1. 基本使用
```bash
# 在 Telegram 中
/skills                    # 打開主選單
/skill_search weather      # 搜索天氣相關技能
/skill_install weather     # 安裝天氣技能
/skill_list                # 查看已安裝技能
```

### 2. 程式化使用
```python
from telegram_handler import get_telegram_handler

handler = get_telegram_handler()

# 搜索技能
result = handler.search_skills("database", limit=5)

# 安裝技能
result = handler.install_skill("postgres-backup")

# 列出已安裝
result = handler.list_installed_skills()
```

### 3. Callback 處理
```python
# 處理 Telegram callback
result = handler.handle_callback("action:search")
result = handler.handle_callback("skill_install:weather")
```

## 測試驗證

### 單元測試
```bash
cd skills-marketplace
python3 test_integration.py
```

### 功能測試
```bash
cd skills-marketplace
python3 demo_telegram.py
```

### 實際安裝測試
```bash
# 測試安裝真實技能
clawhub install weather
clawhub list
```

## 配置選項

### 市場配置 (`config.json`)
```json
{
  "marketplace": {
    "enabled": true,
    "workdir": "/root/.openclaw/workspace",
    "skills_dir": "skills-marketplace/data",
    "auto_update": true,
    "update_interval_hours": 24,
    "search_limit": 10,
    "explore_limit": 10
  }
}
```

### Telegram 配置
```json
{
  "telegram": {
    "enabled": true,
    "parse_mode": "Markdown",
    "keyboard_layout": "inline",
    "button_text_limit": 20
  }
}
```

## 錯誤處理

### 常見錯誤及解決方案
1. **安裝失敗** - 檢查網路連接和權限
2. **搜索無結果** - 嘗試不同關鍵字
3. **更新失敗** - 檢查技能版本兼容性
4. **Callback 錯誤** - 檢查 callback_data 格式

### 日誌位置
- 主日誌: `/root/.openclaw/logs/skills-marketplace.log`
- 錯誤日誌: `/root/.openclaw/logs/skills-marketplace-error.log`

## 效能優化

### 快取策略
- 目錄快取: 24小時更新一次
- 搜索結果: 記憶體快取 1小時
- 已安裝列表: 實時更新

### 資源使用
- 記憶體: < 50MB
- 儲存空間: < 100MB
- 網路請求: 最小化，使用快取

## 安全考慮

### 權限控制
1. 只允許安裝到指定目錄
2. 技能安裝前驗證來源
3. 限制危險操作

### 資料保護
1. 使用者資料本地儲存
2. 不儲存敏感資訊
3. 定期清理快取

## 擴展性

### 未來功能
1. **技能評分系統** - 使用者評分和評論
2. **分類瀏覽** - 按類別瀏覽技能
3. **推薦系統** - 基於使用習慣推薦技能
4. **批量操作** - 批量安裝/卸載
5. **離線模式** - 無網路時使用本地快取

### 插件系統
```python
# 自定義插件範例
class CustomMarketplacePlugin:
    def pre_install(self, slug):
        # 安裝前檢查
        pass
    
    def post_install(self, slug, result):
        # 安裝後處理
        pass
```

## 維護指南

### 日常維護
1. 檢查日誌檔案
2. 清理過期快取
3. 更新 ClawHub CLI

### 故障排除
```bash
# 檢查服務狀態
ps aux | grep python | grep marketplace

# 查看日誌
tail -f /root/.openclaw/logs/skills-marketplace.log

# 重新安裝
cd skills-marketplace && ./install.sh
```

### 備份策略
```bash
# 備份配置
cp -r /root/.openclaw/workspace/skills-marketplace/data /backup/

# 備份已安裝技能
clawhub list > /backup/installed-skills.txt
```

## 貢獻指南

### 開發環境
```bash
# 克隆專案
git clone <repository>
cd skills-marketplace

# 安裝開發依賴
pip install -r requirements-dev.txt

# 運行測試
pytest tests/
```

### 代碼規範
1. 遵循 PEP 8 規範
2. 添加類型提示
3. 編寫單元測試
4. 更新文件

### 提交更改
1. 創建功能分支
2. 編寫測試案例
3. 更新文件
4. 提交 Pull Request

## 聯絡資訊

### 問題回報
- GitHub Issues: [專案地址]
- Telegram: (見管理員設定)
- Email: [聯絡信箱]

### 文件資源
- 使用說明: `README.md`
- API 文件: `API.md`
- 開發指南: `DEVELOPMENT.md`

---

**版本**: 1.0.0  
**更新日期**: 2026-02-11  
**狀態**: ✅ 生產就緒  
**維護者**: OpenClaw AI 助手