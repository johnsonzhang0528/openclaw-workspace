# OpenClaw 功能擴展 - 部署套件

## 📦 套件內容

本部署套件包含四個 OpenClaw 功能擴展：

1. **skills-marketplace/** - 技能市集瀏覽器
2. **workspace-manager/** - 工作空間管理工具  
3. **performance-monitor/** - 效能監控儀表板
4. **smart-shortcuts/** - 智慧快捷指令系統

## 🚀 快速部署

### 自動部署腳本

```bash
# 給予執行權限
chmod +x deploy-all.sh

# 執行部署
./deploy-all.sh
```

### 手動部署步驟

1. **複製技能到 OpenClaw 技能目錄**
   ```bash
   cp -r skills-marketplace /usr/lib/node_modules/openclaw/skills/
   cp -r workspace-manager /usr/lib/node_modules/openclaw/skills/
   cp -r performance-monitor /usr/lib/node_modules/openclaw/skills/
   cp -r smart-shortcuts /usr/lib/node_modules/openclaw/skills/
   ```

2. **更新 OpenClaw 配置**
   ```bash
   # 編輯 OpenClaw 配置檔案
   nano /root/.openclaw/openclaw.json
   
   # 添加技能配置（如果不存在）
   "skills": {
     "skills-marketplace": {
       "enabled": true,
       "telegram_enabled": true
     },
     "workspace-manager": {
       "enabled": true,
       "telegram_enabled": true
     },
     "performance-monitor": {
       "enabled": true,
       "telegram_enabled": true
     },
     "smart-shortcuts": {
       "enabled": true,
       "telegram_enabled": true
     }
   }
   ```

3. **重啟 OpenClaw 服務**
   ```bash
   openclaw gateway restart
   ```

## 🔧 系統要求

### 最低要求
- OpenClaw v1.0.0 或更高版本
- Python 3.8+
- 1GB 可用記憶體
- 100MB 可用磁碟空間

### 推薦配置
- OpenClaw v1.2.0+
- Python 3.10+
- 2GB 可用記憶體
- 500MB 可用磁碟空間
- Telegram Bot Token（用於 Telegram 整合）

## 📋 安裝驗證

### 驗證步驟

1. **檢查技能目錄**
   ```bash
   ls -la /usr/lib/node_modules/openclaw/skills/
   ```

2. **測試技能功能**
   ```bash
   # 在 Telegram 中測試
   /技能市集 狀態
   /工作空間 狀態
   /效能監控 狀態
   /快捷指令 狀態
   ```

3. **查看系統日誌**
   ```bash
   journalctl -u openclaw -f
   ```

### 常見問題解決

#### 技能未顯示
1. 檢查技能目錄權限
2. 確認 OpenClaw 配置正確
3. 重啟 OpenClaw 服務

#### Telegram 命令無效
1. 確認 Telegram Bot Token 正確
2. 檢查技能配置中的 `telegram_enabled`
3. 驗證 Webhook 設置

#### 效能監控無數據
1. 檢查 Python 依賴是否安裝
2. 確認有足夠系統權限
3. 查看技能日誌

## ⚙️ 配置詳解

### 技能市集配置
```json
{
  "skills-marketplace": {
    "enabled": true,
    "telegram_enabled": true,
    "marketplace_url": "https://clawhub.com",
    "cache_duration": 300,
    "update_check_interval": 3600
  }
}
```

### 工作空間管理配置
```json
{
  "workspace-manager": {
    "enabled": true,
    "telegram_enabled": true,
    "default_path": "/root/.openclaw/workspace",
    "max_file_size": 10485760,
    "allowed_extensions": [".py", ".md", ".txt", ".json", ".yaml", ".yml"]
  }
}
```

### 效能監控配置
```json
{
  "performance-monitor": {
    "enabled": true,
    "telegram_enabled": true,
    "collection_interval": 5,
    "alert_thresholds": {
      "cpu": 80,
      "memory": 85,
      "disk": 90
    },
    "retention_days": 7
  }
}
```

### 智慧快捷指令配置
```json
{
  "smart-shortcuts": {
    "enabled": true,
    "telegram_enabled": true,
    "max_shortcuts": 100,
    "template_path": "/root/.openclaw/shortcut-templates",
    "execution_timeout": 30
  }
}
```

## 🔄 更新與升級

### 自動更新
```bash
# 使用技能市集更新功能
/技能市集 更新
```

### 手動更新
1. 備份現有配置
2. 下載新版本套件
3. 覆蓋舊檔案
4. 重啟服務

### 版本遷移
- v1.0.0 → v1.1.0：無需遷移
- 主要版本更新：請參考更新日誌

## 🗑️ 卸載

### 完全卸載
```bash
# 移除技能目錄
rm -rf /usr/lib/node_modules/openclaw/skills/skills-marketplace
rm -rf /usr/lib/node_modules/openclaw/skills/workspace-manager
rm -rf /usr/lib/node_modules/openclaw/skills/performance-monitor
rm -rf /usr/lib/node_modules/openclaw/skills/smart-shortcuts

# 移除配置（可選）
# 編輯 /root/.openclaw/openclaw.json 移除技能配置

# 重啟服務
openclaw gateway restart
```

### 部分卸載
```bash
# 只禁用特定技能
# 編輯 OpenClaw 配置，將對應技能的 enabled 設為 false
```

## 📊 效能報告

### 資源使用
- **記憶體使用**：每個技能約 50-100MB
- **CPU 使用**：空閒時 <1%，活動時 5-10%
- **磁碟空間**：每個技能約 10-20MB

### 優化建議
1. 禁用不需要的技能
2. 調整監控間隔
3. 清理歷史數據
4. 使用緩存機制

## 🔒 安全性

### 權限管理
- 工作空間工具限制訪問路徑
- 快捷指令執行前驗證
- 敏感操作需要確認

### 數據保護
- 配置檔案權限：600
- 日誌輪轉：每天
- 備份建議：每周

### 審計日誌
所有操作都會記錄在：
```
/root/.openclaw/workspace/logs/
```

## 📞 支援

### 獲取幫助
1. 查看使用者文檔：`user-docs.md`
2. 檢查技能內建幫助
3. 查看系統日誌

### 回報問題
請提供：
1. OpenClaw 版本
2. 技能版本
3. 錯誤訊息
4. 重現步驟

### 社區資源
- OpenClaw Discord
- GitHub Repository
- 官方文檔網站

---

**部署套件版本：** v1.0.0  
**創建日期：** 2026-02-11  
**適用系統：** Linux (Ubuntu/Debian/CentOS)