# 監控儀表板技能

## 概述
即時監控子代理任務執行狀態，提供完整的任務管理儀表板。包含任務進度追蹤、資源使用監控、互動式控制和警報系統。

## 功能特點
- 📊 **任務監控**：即時監控子代理任務狀態
- 📈 **進度追蹤**：顯示任務進度百分比和執行時間
- ⚡ **資源監控**：CPU、記憶體使用情況監控
- 🔄 **互動控制**：暫停、繼續、停止任務按鈕
- 🚨 **警報系統**：任務異常自動警報
- 📜 **歷史記錄**：已完成任務統計
- 📱 **多模式顯示**：精簡、詳細、圖表三種模式

## 使用方式

### 基本命令
```
/monitor - 顯示監控儀表板（精簡模式）
/monitor detail - 詳細模式
/monitor chart - 圖表模式
/monitor refresh - 手動刷新
/monitor help - 顯示幫助
```

### 命令別名
```
/dashboard, /status = /monitor
/detail, /full = /monitor detail
/charts, /graph = /monitor chart
/refresh, /update = /monitor refresh
/?, help = /monitor help
```

### Telegram Inline 按鈕
```
📊 精簡模式 - 簡要顯示
📋 詳細模式 - 詳細資訊
📈 圖表模式 - 資源趨勢
🔄 刷新 - 刷新顯示
⏸️  暫停 - 暫停選中任務
▶️  繼續 - 繼續選中任務
⏹️  停止 - 停止選中任務
🚨 警報 - 查看警報
📜 歷史 - 歷史記錄
```

## 技術實現

### 數據來源
- **子代理狀態**：OpenClaw sessions API
- **系統資源**：系統命令 (top, free, df)
- **任務進度**：子代理回報進度
- **執行時間**：會話創建和更新時間戳
- **警報檢測**：資源閾值和異常模式

### 檔案結構
```
monitoring-dashboard/
├── SKILL.md              # 技能描述
├── monitor_bot.py        # 主邏輯
├── telegram_integration.py # Telegram 整合
├── config.json           # 配置檔案
├── scripts/
│   ├── monitor_script.py # 監控腳本
│   └── alert_checker.py  # 警報檢查
├── tests/
│   └── test_monitor.py   # 測試腳本
└── README.md            # 使用說明
```

### 配置範例
```json
{
  "update_interval": 30,
  "max_tasks_display": 10,
  "enable_alerts": true,
  "alert_thresholds": {
    "cpu": 80,
    "memory": 75,
    "duration": 3600,
    "stalled": 300
  },
  "display_modes": {
    "compact": true,
    "detail": true,
    "chart": true
  }
}
```

## 安裝

### 快速安裝
```bash
# 複製技能到技能目錄
cp -r monitoring-dashboard /usr/lib/node_modules/openclaw/skills/

# 重啟 OpenClaw
openclaw gateway restart
```

### 手動整合
1. 將監控腳本複製到工作空間
2. 在 OpenClaw 配置中添加命令處理
3. 設定定時更新任務
4. 重啟服務

## 使用範例

### 1. 精簡模式（預設）
```
/monitor

📊 子代理任務監控儀表板
────────────────────
⏰ 14:36:53 | ⚡ CPU 23.8%
📋 任務: 7個 (3🟢 2🟡 2⚪)

1. 議題系統開發 🟢 65% · 45m
2. 工作空間工具 🟢 30% · 25m
3. 監控系統開發 🟢 15% · 10m
────────────────────
[🔄刷新] [📋詳細] [📈圖表]
```

### 2. 詳細模式
```
/monitor detail

📊 任務監控儀表板 v1.0
────────────────────
狀態概覽：3進行中 · 0失敗 · 2閒置
總執行時間：2小時 15分鐘
系統負載：CPU 45% · RAM 1.2GB/4GB

📋 任務列表：
1. 議題系統互動介面開發
   ├─ 🟢 進行中 · 65% · 45m
   ├─ 📊 CPU 12% · 💾 128MB
   ├─ 📍 開發中：inline keyboard
   └─ ⏳ 預估完成：15分鐘

2. 工作空間管理工具開發
   ├─ 🟢 進行中 · 30% · 25m  
   ├─ 📊 CPU 8% · 💾 96MB
   ├─ 📍 開發中：檔案瀏覽器
   └─ ⏳ 預估完成：45分鐘
────────────────────
```

### 3. 圖表模式
```
/monitor chart

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
────────────────────
```

## 進階功能

### 任務控制
- 暫停執行中的任務
- 繼續暫停的任務
- 停止異常任務
- 重新啟動失敗任務

### 警報系統
- CPU 使用過高警報
- 記憶體洩漏檢測
- 任務停滯警報
- 執行時間過長警報

### 歷史分析
- 24小時任務趨勢
- 資源使用統計
- 成功率分析
- 效能報告生成

## 效能考量
- 增量數據更新
- 快取常用查詢
- 非阻塞式操作
- 記憶體使用優化

## 故障排除

### 常見問題
1. **監控數據不更新**
   - 檢查 OpenClaw 服務狀態
   - 確認會話 API 可用

2. **按鈕無回應**
   - 檢查 Telegram 整合配置
   - 確認回調處理正確

3. **警報不觸發**
   - 檢查閾值配置
   - 確認警報檢查間隔

### 日誌位置
- 監控日誌：`/var/log/openclaw/monitor.log`
- 錯誤日誌：`/var/log/openclaw/error.log`

## 開發指南

### 添加新監控指標
1. 在 `monitor_bot.py` 中添加數據收集函數
2. 更新顯示格式化函數
3. 添加對應的配置選項

### 擴展顯示模式
編輯 `format_compact()`、`format_detail()`、`format_chart()` 函數

### 添加新控制功能
在 `handle_button_click()` 中添加新的按鈕處理邏輯

## 版本歷史
- v1.0.0：基礎監控功能
- v1.1.0：添加任務控制
- v1.2.0：添加警報系統
- v1.3.0：多模式顯示

## 授權
MIT License

## 貢獻
歡迎提交 Issue 和 Pull Request

## 聯絡
- GitHub: [OpenClaw](https://github.com/openclaw/openclaw)
- Discord: [OpenClaw Community](https://discord.com/invite/clawd)