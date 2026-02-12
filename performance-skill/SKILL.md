# 效能監控技能

## 概述
即時監控系統效能，無需安裝額外依賴，使用系統命令獲取 CPU、記憶體、磁碟、網路等資源使用情況。

## 功能特點
- 🚀 **零依賴**：使用系統命令，無需安裝 psutil
- 📊 **即時監控**：CPU、記憶體、磁碟、網路使用率
- 🔥 **進程分析**：顯示資源消耗最多的進程
- 📈 **系統統計**：詳細硬體和系統資訊
- 📱 **Telegram 整合**：inline keyboard 互動控制
- ⚡ **快速響應**：命令執行速度快

## 使用方式

### 基本命令
```
/performance - 顯示系統效能報告
/processes - 顯示熱門進程
/stats - 顯示詳細系統統計
/help - 顯示幫助訊息
```

### 命令別名
```
/perf, /sysinfo = /performance
/top, /procs = /processes  
/statistics, /details = /stats
/?, help = /help
```

### Telegram Inline 按鈕
```
📊 系統效能 - 顯示即時效能
🔥 熱門進程 - 顯示資源消耗最多的進程
📋 詳細統計 - 顯示系統詳細資訊
🔄 刷新 - 刷新當前視圖
❓ 幫助 - 顯示幫助
```

## 技術實現

### 數據來源
- **CPU 使用率**：`top -bn1` 命令
- **記憶體使用**：`free -h` 命令
- **磁碟使用**：`df -h` 命令
- **系統負載**：`cat /proc/loadavg`
- **進程資訊**：`top -bn1 -o %CPU`
- **系統資訊**：`uname`, `nproc`, `/etc/os-release`

### 檔案結構
```
performance-skill/
├── SKILL.md              # 技能描述
├── performance_bot.py    # 主邏輯
├── telegram_integration.py # Telegram 整合
├── config.json           # 配置檔案
└── README.md            # 使用說明
```

### 配置範例
```json
{
  "update_interval": 5,
  "max_processes": 8,
  "enable_alerts": true,
  "alert_thresholds": {
    "cpu": 90,
    "memory": 85,
    "disk": 90
  }
}
```

## 安裝

### 快速安裝
```bash
# 複製技能到技能目錄
cp -r performance-skill /usr/lib/node_modules/openclaw/skills/

# 重啟 OpenClaw
openclaw gateway restart
```

### 手動整合
1. 將 `performance_bot.py` 複製到工作空間
2. 在 OpenClaw 配置中添加命令處理
3. 重啟服務

## 使用範例

### 1. 基本效能監控
```
/performance

📊 即時系統效能報告
⏰ 2026-02-12 02:36:27

⏱️  02:36:27 up 1 day, 2:38, 3 users, load average: 0.10, 0.10, 0.04
⚡ CPU: 0.0% 使用
🧠 記憶體: 5.5Gi/7.5Gi 使用
💾 磁碟: 8% 使用
📈 系統負載: 0.10 (0.10/0.04)
🔢 進程數: 155
🌐 網路連接: 9
```

### 2. 熱門進程
```
/processes

🔥 資源消耗最多的進程

📊 1. systemd
   PID: 1 | CPU: 0.0% | 記憶體: 0.2%
📊 2. kthreadd
   PID: 2 | CPU: 0.0% | 記憶體: 0.0%
```

### 3. 系統統計
```
/stats

📋 系統詳細統計

🖥️  CPU 核心數: 4
🧠 總記憶體: 7.5Gi
💾 總磁碟空間: 75G
🏗️  系統架構: aarch64
🐧 作業系統: Ubuntu 24.04.3 LTS
```

## 進階功能

### 自定義監控
可以修改 `performance_bot.py` 添加：
- 網路流量監控
- 溫度監控
- 服務狀態檢查
- 日誌分析

### 警報系統
實現資源使用過高時的警報：
- CPU > 90% 持續 1分鐘
- 記憶體 > 85% 使用率
- 磁碟 > 90% 使用率

### 歷史記錄
添加數據記錄功能：
- 24小時趨勢圖
- 每日報告
- 效能異常檢測

## 效能考量
- 命令執行輕量級
- 無常駐進程
- 記憶體使用少
- 響應速度快

## 故障排除

### 常見問題
1. **命令執行失敗**
   - 檢查命令執行權限
   - 確認系統命令可用

2. **數據不準確**
   - 更新系統命令版本
   - 檢查命令參數

3. **Telegram 無回應**
   - 檢查 OpenClaw 連接
   - 確認技能配置正確

### 日誌位置
- OpenClaw 日誌：`/var/log/openclaw/`
- 系統日誌：`/var/log/syslog`

## 開發指南

### 添加新命令
1. 在 `performance_bot.py` 中添加處理函數
2. 在 `handle_command` 中註冊命令
3. 更新 `get_help` 函數

### 修改顯示格式
編輯 `format_system_info`、`format_top_processes` 等函數

### 擴展數據來源
添加新的系統命令解析函數

## 版本歷史
- v1.0.0：基礎監控功能
- v1.1.0：添加進程監控
- v1.2.0：添加系統統計
- v1.3.0：Telegram 整合

## 授權
MIT License

## 貢獻
歡迎提交 Issue 和 Pull Request

## 聯絡
- GitHub: [OpenClaw](https://github.com/openclaw/openclaw)
- Discord: [OpenClaw Community](https://discord.com/invite/clawd)