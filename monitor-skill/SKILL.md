# 監控儀表板技能

## 概述
即時監控系統效能和子代理任務狀態的儀表板技能。提供精簡、詳細和圖表三種顯示模式，支援 Telegram inline keyboard 互動控制。

## 功能特色
- 📊 **即時系統監控**：CPU、記憶體、磁碟、網路使用率
- 🤖 **子代理任務監控**：監控正在執行的子代理任務狀態
- ⏱️ **執行時間追蹤**：每個任務的執行時間和進度
- 🚨 **警報系統**：資源使用過高時自動警報
- 📈 **多種顯示模式**：精簡、詳細、圖表模式
- 🔄 **互動控制**：暫停、繼續、停止任務按鈕
- 📱 **Telegram 整合**：inline keyboard 互動

## 使用方式

### 基本命令
```
/monitor - 顯示監控儀表板（精簡模式）
/monitor detailed - 顯示詳細監控儀表板
/monitor charts - 顯示圖表模式
/performance - 顯示系統效能報告
/tasks - 顯示子代理任務列表
/alerts - 顯示當前警報
/help - 顯示幫助訊息
```

### 命令別名
```
/mon, /dashboard = /monitor
/perf, /sysinfo = /performance
/status, /list = /tasks
/warnings, /notifications = /alerts
/?, help = /help
```

### Telegram Inline 按鈕
```
📊 監控儀表板 - 顯示即時監控
🔍 詳細模式 - 顯示詳細資訊
📈 圖表模式 - 顯示資源圖表
🔄 刷新 - 刷新當前視圖
⚡ 效能報告 - 顯示系統效能
📋 任務列表 - 顯示子代理任務
🚨 警報列表 - 顯示當前警報
❓ 幫助 - 顯示幫助
```

## 顯示模式

### 精簡模式（預設）
```
📊 監控儀表板
────────────────────
⚡ CPU: 4.8%
🧠 記憶體: 1.6Gi/7.5Gi (21%)
💾 磁碟: 5.5G/75G (8%)
📈 負載: 0.16 0.13 0.06

🤖 子代理任務
🟢 執行中: 0
🟡 閒置中: 4
⚪ 已停止: 3
📋 總數: 7
────────────────────
```

### 詳細模式
```
📊 詳細監控儀表板
────────────────────
⏰ 更新時間: 14:38:04

系統狀態
├─ ⚡ CPU 使用率: 4.8%
├─ 🧠 記憶體使用: 1.6Gi/7.5Gi (21%)
├─ 💾 磁碟使用: 5.5G/75G (8%)
├─ 📈 系統負載: 0.16 0.13 0.06
└─ 🌡️  系統溫度: 45°C

子代理任務 (7個)
├─ 1. 議題系統互動介面開發
│  ├─ 🟡 閒置中 · 1分鐘前
│  ├─ ⏱️  執行時間: 45m
│  └─ 🔗 ID: 27a3c030...
├─ 2. 工作空間管理工具開發
│  ├─ 🟡 閒置中 · 4分鐘前
│  ├─ ⏱️  執行時間: 25m
│  └─ 🔗 ID: 9f5b672b...
└─ 3. 任務進度監控系統開發
   ├─ 🟡 閒置中 · 4分鐘前
   ├─ ⏱️  執行時間: 10m
   └─ 🔗 ID: ddd47fb2...
────────────────────
```

### 圖表模式
```
📈 資源使用趨勢圖
────────────────────
CPU 使用率 (%)
60 ┤         ╭─╮
50 ┤       ╭─╯ ╰─╮
40 ┤     ╭─╯     ╰─╮
30 ┤   ╭─╯         ╰─╮
20 ┤ ╭─╯             ╰─╮
10 ┼─╯                 ╰─
   └────────────────────
    10m  20m  30m  40m  50m

記憶體使用 (GB)
6.0 ┤               ╭─╮
4.5 ┤             ╭─╯ ╰─╮
3.0 ┤           ╭─╯     ╰─╮
1.5 ┤         ╭─╯         ╰─╮
0.0 ┼─────────╯             ╰─
   └────────────────────
    10m  20m  30m  40m  50m
────────────────────
```

## 技術實現

### 數據來源
- **系統監控**：`top`, `free`, `df`, `/proc/loadavg`
- **子代理任務**：OpenClaw sessions API
- **資源使用**：系統命令和 psutil 庫
- **歷史數據**：本地 JSON 檔案儲存

### 檔案結構
```
monitor-skill/
├── SKILL.md                    # 技能描述檔案
├── monitor_bot.py              # 主邏輯腳本
├── telegram_integration.py     # Telegram 整合
├── config.json                 # 配置檔案
├── requirements.txt            # Python 依賴
└── README.md                   # 使用說明
```

### 配置範例 (config.json)
```json
{
  "update_interval": 30,
  "max_tasks_display": 10,
  "enable_alerts": true,
  "alert_thresholds": {
    "cpu": 80,
    "memory": 85,
    "disk": 90
  },
  "telegram": {
    "enabled": true,
    "inline_buttons": true,
    "refresh_button": true
  },
  "history": {
    "enabled": true,
    "max_days": 7,
    "max_entries": 1000
  }
}
```

## 安裝

### 快速安裝
```bash
# 複製技能到技能目錄
cp -r monitor-skill /usr/lib/node_modules/openclaw/skills/

# 安裝 Python 依賴
pip install -r monitor-skill/requirements.txt

# 重啟 OpenClaw
openclaw gateway restart
```

### 手動整合
1. 將 `monitor_bot.py` 複製到工作空間
2. 在 OpenClaw 配置中添加命令處理
3. 重啟服務

## 使用範例

### 1. 基本監控
```
/monitor

📊 監控儀表板
────────────────────
⚡ CPU: 4.8%
🧠 記憶體: 1.6Gi/7.5Gi (21%)
💾 磁碟: 5.5G/75G (8%)
📈 負載: 0.16 0.13 0.06

🤖 子代理任務
🟢 執行中: 0
🟡 閒置中: 4
⚪ 已停止: 3
📋 總數: 7
────────────────────
```

### 2. 詳細監控
```
/monitor detailed

📊 詳細監控儀表板
────────────────────
⏰ 更新時間: 14:38:04

系統狀態
├─ ⚡ CPU 使用率: 4.8%
├─ 🧠 記憶體使用: 1.6Gi/7.5Gi (21%)
├─ 💾 磁碟使用: 5.5G/75G (8%)
├─ 📈 系統負載: 0.16 0.13 0.06
└─ 🌡️  系統溫度: 45°C
```

### 3. 任務列表
```
/tasks

📋 子代理任務列表
────────────────────
1. 議題系統互動介面開發
   ├─ 🟡 閒置中 · 1分鐘前
   ├─ ⏱️  執行時間: 45m
   └─ 🔗 ID: 27a3c030...

2. 工作空間管理工具開發
   ├─ 🟡 閒置中 · 4分鐘前
   ├─ ⏱️  執行時間: 25m
   └─ 🔗 ID: 9f5b672b...

3. 任務進度監控系統開發
   ├─ 🟡 閒置中 · 4分鐘前
   ├─ ⏱️  執行時間: 10m
   └─ 🔗 ID: ddd47fb2...
────────────────────
```

## 進階功能

### 自定義監控
可以修改配置添加：
- 網路流量監控
- 服務狀態檢查
- 自定義警報規則
- 通知頻道設定

### 警報系統
實現資源使用過高時的警報：
- CPU > 80% 持續 1分鐘
- 記憶體 > 85% 使用率
- 磁碟 > 90% 使用率
- 任務執行超時

### 歷史記錄
添加數據記錄功能：
- 24小時趨勢圖
- 每日報告
- 效能異常檢測
- 任務統計分析

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
- 技能日誌：`monitor-skill/logs/`

## 開發指南

### 添加新命令
1. 在 `monitor_bot.py` 中添加處理函數
2. 在 `handle_command` 中註冊命令
3. 更新 `get_help` 函數

### 修改顯示格式
編輯顯示格式化函數：
- `format_compact_dashboard`
- `format_detailed_dashboard`
- `format_charts_dashboard`

### 擴展數據來源
添加新的數據收集函數：
- 網路監控
- 溫度監控
- 服務狀態檢查

## 版本歷史
- v1.0.0：基礎監控功能
- v1.1.0：添加子代理任務監控
- v1.2.0：添加詳細和圖表模式
- v1.3.0：Telegram inline keyboard 整合

## 授權
MIT License

## 貢獻
歡迎提交 Issue 和 Pull Request

## 聯絡
- GitHub: [OpenClaw](https://github.com/openclaw/openclaw)
- Discord: [OpenClaw Community](https://discord.com/invite/clawd)