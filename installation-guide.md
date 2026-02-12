# OpenClaw 功能擴展安裝指南

## 📋 概述

本指南詳細介紹如何安裝和配置 OpenClaw 的四個功能擴展：
1. **技能市集瀏覽器** - 瀏覽和安裝第三方技能
2. **工作空間管理工具** - 檔案瀏覽和編輯工具  
3. **效能監控儀表板** - 系統資源監控和警報
4. **智慧快捷指令系統** - 自定義指令和模板系統

## 🎯 安裝前準備

### 系統要求

#### 最低配置
- **作業系統**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **CPU**: 2 核心
- **記憶體**: 2GB RAM
- **磁碟空間**: 20GB 可用空間
- **網路**: 穩定的網路連接

#### 推薦配置
- **作業系統**: Ubuntu 22.04+ / Debian 12+
- **CPU**: 4 核心
- **記憶體**: 4GB RAM  
- **磁碟空間**: 50GB SSD
- **網路**: 100Mbps 以上

### 軟體依賴

#### 必需軟體
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip git curl wget

# CentOS/RHEL
sudo yum install -y python3 python3-pip git curl wget
```

#### Python 套件
```bash
# 安裝必需 Python 套件
pip3 install psutil requests python-telegram-bot
```

#### OpenClaw 要求
- OpenClaw v1.0.0 或更高版本
- Telegram Bot Token（用於 Telegram 整合）

### 環境檢查

運行環境檢查腳本：
```bash
# 下載檢查腳本
curl -O https://raw.githubusercontent.com/openclaw/openclaw/main/scripts/env-check.sh
chmod +x env-check.sh
./env-check.sh
```

## 🚀 快速安裝

### 方法一：一鍵安裝腳本（推薦）

```bash
# 下載安裝腳本
wget https://clawhub.com/install/openclaw-extensions.sh
chmod +x openclaw-extensions.sh

# 執行安裝
sudo ./openclaw-extensions.sh
```

安裝過程會自動：
1. 檢查系統環境
2. 安裝依賴套件
3. 部署技能檔案
4. 配置 OpenClaw
5. 重啟服務

### 方法二：手動安裝

#### 步驟 1：下載技能套件
```bash
# 創建臨時目錄
mkdir -p /tmp/openclaw-extensions
cd /tmp/openclaw-extensions

# 下載技能套件
wget https://clawhub.com/releases/openclaw-extensions-v1.0.0.tar.gz
tar -xzf openclaw-extensions-v1.0.0.tar.gz
cd openclaw-extensions-v1.0.0
```

#### 步驟 2：部署技能
```bash
# 複製技能到 OpenClaw 目錄
sudo cp -r skills-marketplace /usr/lib/node_modules/openclaw/skills/
sudo cp -r workspace-manager /usr/lib/node_modules/openclaw/skills/
sudo cp -r performance-monitor /usr/lib/node_modules/openclaw/skills/
sudo cp -r smart-shortcuts /usr/lib/node_modules/openclaw/skills/

# 設置權限
sudo chmod -R 755 /usr/lib/node_modules/openclaw/skills/
```

#### 步驟 3：配置 OpenClaw
```bash
# 編輯 OpenClaw 配置
sudo nano /root/.openclaw/openclaw.json
```

添加以下配置：
```json
{
  "skills": {
    "skills-marketplace": {
      "enabled": true,
      "telegram_enabled": true,
      "marketplace_url": "https://clawhub.com",
      "cache_duration": 300,
      "update_check_interval": 3600
    },
    "workspace-manager": {
      "enabled": true,
      "telegram_enabled": true,
      "default_path": "/root/.openclaw/workspace",
      "max_file_size": 10485760,
      "allowed_extensions": [".py", ".md", ".txt", ".json", ".yaml", ".yml"]
    },
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
    },
    "smart-shortcuts": {
      "enabled": true,
      "telegram_enabled": true,
      "max_shortcuts": 100,
      "template_path": "/root/.openclaw/shortcut-templates",
      "execution_timeout": 30
    }
  }
}
```

#### 步驟 4：重啟服務
```bash
# 重啟 OpenClaw
sudo systemctl restart openclaw
# 或
openclaw gateway restart
```

## 🔧 進階安裝

### Docker 安裝

#### Docker Compose 配置
```yaml
version: '3.8'

services:
  openclaw:
    image: openclaw/openclaw:latest
    container_name: openclaw
    restart: unless-stopped
    volumes:
      - ./data:/root/.openclaw
      - ./skills:/usr/lib/node_modules/openclaw/skills
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - OPENCLAW_EXTENSIONS_ENABLED=true
    ports:
      - "3000:3000"
```

#### 部署步驟
```bash
# 1. 創建目錄結構
mkdir -p openclaw-data/{skills,config,logs}

# 2. 複製技能
cp -r skills-marketplace openclaw-data/skills/
cp -r workspace-manager openclaw-data/skills/
cp -r performance-monitor openclaw-data/skills/
cp -r smart-shortcuts openclaw-data/skills/

# 3. 創建環境變數檔案
echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env

# 4. 啟動服務
docker-compose up -d
```

### Kubernetes 安裝

#### Helm Chart 配置
```yaml
# values.yaml
openclaw:
  extensions:
    enabled: true
    skills:
      marketplace:
        enabled: true
      workspace:
        enabled: true
      performance:
        enabled: true
      shortcuts:
        enabled: true
```

#### 部署命令
```bash
# 添加 Helm 倉庫
helm repo add openclaw https://charts.openclaw.ai
helm repo update

# 安裝 OpenClaw
helm install openclaw openclaw/openclaw \
  --namespace openclaw \
  --create-namespace \
  --values values.yaml
```

## ⚙️ 安裝後配置

### Telegram 配置

#### 獲取 Bot Token
1. 在 Telegram 中聯繫 @BotFather
2. 發送 `/newbot` 創建新機器人
3. 按照提示設置名稱和用戶名
4. 獲取 API Token

#### 配置 Webhook
```bash
# 設置 Webhook
curl -F "url=https://your-domain.com/webhook" \
     https://api.telegram.org/bot{YOUR_BOT_TOKEN}/setWebhook
```

#### 測試 Telegram 連接
```bash
# 測試機器人
curl https://api.telegram.org/bot{YOUR_BOT_TOKEN}/getMe
```

### 技能配置

#### 技能市集配置
```bash
# 創建技能市集配置目錄
mkdir -p /root/.openclaw/skills-marketplace

# 配置技能源
cat > /root/.openclaw/skills-marketplace/config.json << EOF
{
  "sources": [
    "https://clawhub.com/api/v1/skills",
    "https://github.com/openclaw/skills"
  ],
  "cache_ttl": 3600,
  "auto_update": true
}
EOF
```

#### 工作空間配置
```bash
# 設置預設工作空間
mkdir -p /root/.openclaw/workspace
chmod 755 /root/.openclaw/workspace
```

#### 效能監控配置
```bash
# 創建監控數據目錄
mkdir -p /root/.openclaw/performance-data
chmod 755 /root/.openclaw/performance-data
```

#### 快捷指令配置
```bash
# 創建模板目錄
mkdir -p /root/.openclaw/shortcut-templates
chmod 755 /root/.openclaw/shortcut-templates

# 添加預設模板
cp /usr/lib/node_modules/openclaw/skills/smart-shortcuts/templates/* \
   /root/.openclaw/shortcut-templates/
```

## ✅ 安裝驗證

### 基本驗證

#### 檢查技能檔案
```bash
# 檢查技能目錄
ls -la /usr/lib/node_modules/openclaw/skills/

# 檢查技能檔案
ls -la /usr/lib/node_modules/openclaw/skills/skills-marketplace/
ls -la /usr/lib/node_modules/openclaw/skills/workspace-manager/
ls -la /usr/lib/node_modules/openclaw/skills/performance-monitor/
ls -la /usr/lib/node_modules/openclaw/skills/smart-shortcuts/
```

#### 檢查配置
```bash
# 檢查 OpenClaw 配置
cat /root/.openclaw/openclaw.json | python3 -m json.tool
```

### 功能測試

#### 測試技能命令
```bash
# 在 Telegram 中測試以下命令：
/技能市集 狀態
/工作空間 狀態
/效能監控 狀態
/快捷指令 狀態
```

#### 測試快捷命令
```bash
# 測試快捷命令：
/sm    # 技能市集
/ws    # 工作空間
/pm    # 效能監控
/sc    # 快捷指令
```

### 系統檢查

#### 檢查服務狀態
```bash
# 檢查 OpenClaw 服務
systemctl status openclaw

# 檢查日誌
journalctl -u openclaw -f
```

#### 檢查網路連接
```bash
# 測試外部連接
curl -I https://clawhub.com

# 測試 Telegram API
curl https://api.telegram.org/bot{YOUR_BOT_TOKEN}/getWebhookInfo
```

## 🐛 故障排除

### 常見問題

#### 問題 1：技能未顯示
```bash
# 解決方案：
1. 檢查技能目錄權限
   sudo chmod -R 755 /usr/lib/node_modules/openclaw/skills/

2. 檢查配置檔案
   cat /root/.openclaw/openclaw.json | grep -A5 "skills"

3. 重啟 OpenClaw
   sudo systemctl restart openclaw
```

#### 問題 2：Telegram 命令無效
```bash
# 解決方案：
1. 檢查 Bot Token
   echo $TELEGRAM_BOT_TOKEN

2. 檢查 Webhook
   curl https://api.telegram.org/bot{YOUR_BOT_TOKEN}/getWebhookInfo

3. 重新設置 Webhook
   curl -X POST https://api.telegram.org/bot{YOUR_BOT_TOKEN}/deleteWebhook
   curl -F "url=https://your-domain.com/webhook" \
        https://api.telegram.org/bot{YOUR_BOT_TOKEN}/setWebhook
```

#### 問題 3：效能監控無數據
```bash
# 解決方案：
1. 檢查 Python 依賴
   pip3 list | grep psutil

2. 檢查權限
   ls -la /proc/stat

3. 查看技能日誌
   tail -f /root/.openclaw/workspace/logs/performance-monitor.log
```

#### 問題 4：記憶體使用過高
```bash
# 解決方案：
1. 調整配置
   # 編輯 /root/.openclaw/openclaw.json
   # 減少 cache_duration 和 retention_days

2. 限制技能功能
   # 禁用不需要的功能

3. 增加系統記憶體
   # 考慮升級伺服器配置
```

### 日誌分析

#### 查看技能日誌
```bash
# 技能市集日誌
tail -f /root/.openclaw/workspace/logs/skills-marketplace.log

# 工作空間日誌
tail -f /root/.openclaw/workspace/logs/workspace-manager.log

# 效能監控日誌
tail -f /root/.openclaw/workspace/logs/performance-monitor.log

# 快捷指令日誌
tail -f /root/.openclaw/workspace/logs/smart-shortcuts.log
```

#### 系統日誌
```bash
# OpenClaw 系統日誌
journalctl -u openclaw -f

# 系統資源日誌
dmesg | tail -20

# 網路連接日誌
ss -tulpn | grep openclaw
```

## 🔄 更新與升級

### 檢查更新
```bash
# 使用技能市集檢查更新
/技能市集 更新

# 或手動檢查
curl -s https://clawhub.com/api/v1/version | jq .
```

### 更新技能
```bash
# 自動更新
/技能市集 更新全部

# 手動更新特定技能
/技能市集 更新 技能名稱
```

### 版本遷移

#### 從 v0.x 升級到 v1.0
```bash
# 1. 備份現有配置
cp /root/.openclaw/openclaw.json /root/.openclaw/openclaw.json.backup

# 2. 停止服務
systemctl stop openclaw

# 3. 更新技能檔案
# （使用新的安裝包覆蓋舊檔案）

# 4. 更新配置
# （參考新的配置格式）

# 5. 啟動服務
systemctl start openclaw
```

## 🗑️ 卸載

### 完全卸載
```bash
# 1. 停止服務
systemctl stop openclaw

# 2. 移除技能目錄
rm -rf /usr/lib/node_modules/openclaw/skills/skills-marketplace
rm -rf /usr/lib/node_modules/openclaw/skills/workspace-manager
rm -rf /usr/lib/node_modules/openclaw/skills/performance-monitor
rm -rf /usr/lib/node_modules/openclaw/skills/smart-shortcuts

# 3. 清理配置
# 編輯 /root/.openclaw/openclaw.json 移除技能配置

# 4. 清理數據（可選）
rm -rf /root/.openclaw/skills-marketplace
rm -rf /root/.openclaw/performance-data
rm -rf /root/.openclaw/shortcut-templates

# 5. 重啟服務
systemctl start openclaw
```

### 部分卸載
```bash
# 只卸載特定技能
rm -rf /usr/lib/node_modules/openclaw/skills/技能名稱

# 在配置中禁用技能
# 編輯 /root/.openclaw/openclaw.json
# 將對應技能的 enabled 設為 false
```

## 📞 支援與幫助

### 獲取幫助
```bash
# 技能內建幫助
/技能市集 幫助
/工作空間 幫助
/效能監控 幫助
/快捷指令 幫助

# 查看文檔
cat /usr/share/doc/openclaw-extensions/README.md
```

### 社區支援
- **Discord**: https://discord.gg/clawd
- **GitHub**: https://github.com/openclaw/openclaw
- **文檔**: https://docs.openclaw.ai

### 回報問題
請提供以下資訊：
1. OpenClaw 版本：`openclaw --version`
2. 系統資訊：`uname -a`
3. 錯誤日誌：相關技能日誌
4. 重現步驟：詳細的操作步驟

---

**安裝指南版本：** v1.0.0  
**最後更新：** 2026-02-11  
**適用版本：** OpenClaw 功能擴展 v1.0.0  

**注意事項：**
1. 生產環境請先進行測試安裝
2. 定期備份重要數據
3. 關注安全更新
4. 參考官方文檔獲取最新資訊