# 監控儀表板技能

## 概述
即時監控 OpenClaw 子代理任務執行狀態的儀表板系統。提供任務狀態追蹤、資源使用監控和互動式控制功能。

## 功能特色

### 📊 任務監控
- 即時顯示子代理任務狀態
- 任務進度追蹤
- 執行時間監控
- 活動記錄查看

### ⚡ 資源監控
- CPU 使用率監控
- 記憶體使用情況
- 系統負載顯示
- 資源趨勢圖表

### 🔄 互動控制
- 多模式顯示（精簡/詳細/圖表）
- Telegram inline keyboard 控制
- 任務暫停/繼續/停止
- 即時刷新功能

### 🚨 警報系統
- 資源使用過高警報
- 任務超時警報
- 進度異常檢測
- 警報歷史記錄

## 快速開始

### 安裝
```bash
# 複製技能到技能目錄
cp -r monitoring-dashboard /usr/lib/node_modules/openclaw/skills/

# 重啟 OpenClaw
openclaw gateway restart
```

### 基本使用
```
# 顯示監控儀表板
/monitor

# 詳細模式
/monitor detail

# 圖表模式
/monitor chart

# 幫助訊息
/monitor help
```

## 命令參考

### 主要命令
| 命令 | 別名 | 說明 |
|------|------|------|
| `/monitor` | `/dashboard`, `/status` | 顯示精簡模式儀表板 |
| `/monitor detail` | `/detail`, `/full` | 顯示詳細模式儀表板 |
| `/monitor chart` | `/charts`, `/graph` | 顯示圖表模式儀表板 |
| `/monitor refresh` | `/refresh`, `/update` | 手動刷新顯示 |
| `/monitor help` | `/?`, `help` | 顯示幫助訊息 |

### Telegram 按鈕
| 按鈕 | 功能 | 說明 |
|------|------|------|
| 📊 精簡 | 切換精簡模式 | 簡要顯示任務狀態 |
| 📋 詳細 | 切換詳細模式 | 顯示詳細任務資訊 |
| 📈 圖表 | 切換圖表模式 | 顯示資源使用趨勢 |
| 🔄 刷新 | 刷新顯示 | 更新監控數據 |
| 🚨 警報 | 查看警報 | 顯示系統警報列表 |
| 📜 歷史 | 查看歷史 | 顯示任務歷史記錄 |
| ⏸️ 暫停 | 暫停任務 | 暫停選中任務 |
| ▶️ 繼續 | 繼續任務 | 繼續暫停的任務 |
| ⏹️ 停止 | 停止任務 | 停止異常任務 |

## 顯示模式

### 精簡模式（預設）
```
📊 子代理任務監控儀表板
────────────────────────
⏰ 14:36:53 | ⚡ CPU 23.8%
📋 任務: 7個 (3🟢 2🟡 2⚪)

1. 議題系統開發 🟢 65% · 45m
2. 工作空間工具 🟢 30% · 25m
3. 監控系統開發 🟢 15% · 10m
────────────────────────
```

### 詳細模式
```
📊 任務監控儀表板 - 詳細模式
────────────────────────────────────
⏰ 更新時間: 14:36:53
⚡ CPU 使用率: 23.8%
🧠 記憶體使用: 1.7Gi/7.5Gi
📈 系統負載: 0.18 0.12 0.05
────────────────────────────────────
📋 總任務數量: 3 個

1. 議題系統互動介面開發
   ├─ 狀態: 🟢 running
   ├─ 最後活動: 剛剛
   ├─ 執行時間: 45分鐘
   └─ 會話ID: 27a3c030...
```

### 圖表模式
```
📈 資源使用趨勢圖
────────────────────────────────────
⏰ 更新時間: 14:36:53

CPU 使用率 (%)
100 ┤ ██████████
 90 ┤ █████████░
 80 ┤ ████████░░
 70 ┤ ███████░░░
 60 ┤ ██████░░░░
 50 ┤ █████░░░░░
 40 ┤ ████░░░░░░
 30 ┤ ███░░░░░░░
 20 ┤ ██░░░░░░░░
 10 ┤ █░░░░░░░░░
  0 ┤ ░░░░░░░░░░
```

## 配置說明

### 配置檔案位置
`config/settings.yaml`

### 主要配置項目
```yaml
dashboard:
  refresh_interval: 30      # 更新間隔（秒）
  max_tasks: 20            # 最大顯示任務數
  history_days: 7          # 歷史記錄保留天數

monitoring:
  cpu_threshold: 80        # CPU 使用率閾值（%）
  memory_threshold: 90     # 記憶體使用率閾值（%）
  timeout_minutes: 60      # 任務超時時間（分鐘）

alerts:
  enabled: true           # 啟用警報系統
```

## 檔案結構
```
monitoring-dashboard/
├── SKILL.md              # 技能描述檔案
├── monitor_bot.py        # 主監控邏輯
├── telegram_integration.py # Telegram 整合
├── config/
│   └── settings.yaml     # 配置檔案
├── scripts/
│   └── monitor_script.py # 輔助腳本
├── tests/
│   └── test_monitor.py   # 測試腳本
└── README.md            # 使用說明
```

## 開發指南

### 添加新監控指標
1. 在 `monitor_bot.py` 中添加數據收集函數
2. 更新顯示格式化函數
3. 添加對應的配置選項

### 擴展顯示模式
編輯 `generate_compact_dashboard()`、`generate_detailed_dashboard()`、`generate_chart_dashboard()` 函數

### 添加新控制功能
在 `telegram_integration.py` 的 `handle_callback()` 中添加新的按鈕處理邏輯

## 故障排除

### 常見問題
1. **監控數據不更新**
   - 檢查 OpenClaw 服務狀態
   - 確認會話 API 可用性
   - 檢查配置檔案中的更新間隔

2. **Telegram 按鈕無回應**
   - 檢查 Telegram 整合配置
   - 確認回調處理函數正確
   - 檢查按鈕 callback_data 格式

3. **系統資源顯示不準確**
   - 確認系統命令可用性
   - 檢查命令執行權限
   - 更新系統命令版本

### 日誌位置
- 監控日誌：`logs/monitoring_dashboard.log`
- 錯誤日誌：OpenClaw 系統日誌

## 效能優化

### 數據更新策略
- 增量更新任務狀態
- 快取系統資源數據
- 非阻塞式數據獲取

### 記憶體管理
- 限制歷史記錄數量
- 定期清理緩存數據
- 優化數據結構

## 版本歷史

### v1.0.0 (2026-02-12)
- 基礎監控功能
- 三種顯示模式
- Telegram 整合
- 基本警報系統

### v1.1.0 (計劃中)
- 增強警報系統
- 歷史記錄分析
- 效能優化
- 更多監控指標

## 授權
MIT License

## 貢獻
歡迎提交 Issue 和 Pull Request

## 聯絡
- GitHub: [OpenClaw](https://github.com/openclaw/openclaw)
- Discord: [OpenClaw Community](https://discord.com/invite/clawd)