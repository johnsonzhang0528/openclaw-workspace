# 效能監控技能

## 概述
即時監控系統效能，提供 CPU、記憶體、磁碟、網路等資源使用情況的圖形化報告。

## 功能
- 📊 **即時監控**：CPU、記憶體、磁碟、網路使用率
- 📈 **歷史趨勢**：24小時效能趨勢圖
- ⚠️ **警報系統**：資源使用過高時自動警報
- 🔍 **進程分析**：查看資源消耗最多的進程
- 📱 **Telegram 介面**：inline keyboard 互動控制

## 使用方式

### 命令
```
/performance - 顯示即時效能報告
/performance history - 顯示歷史趨勢
/performance alerts - 查看警報狀態
/performance top - 顯示資源消耗最多的進程
```

### Telegram 按鈕
- 📊 即時報告
- 📈 歷史趨勢  
- ⚠️ 警報狀態
- 🔥 熱門進程
- 🔄 刷新數據

## 技術架構

### 主要模組
1. **resource_monitor.py** - 資源監控核心
2. **dashboard.py** - 儀表板顯示
3. **alert_system.py** - 警報系統
4. **telegram_ui.py** - Telegram 介面
5. **data_store.py** - 數據儲存

### 數據收集
- CPU 使用率（每5秒）
- 記憶體使用（每5秒）
- 磁碟 I/O（每10秒）
- 網路流量（每10秒）
- 系統負載（每30秒）

### 警報閾值
- CPU > 90% 持續 1分鐘
- 記憶體 > 85% 持續 30秒
- 磁碟 > 90% 使用率
- 負載 > CPU核心數 * 2

## 配置

### 環境變數
```bash
PERFORMANCE_UPDATE_INTERVAL=5  # 更新間隔（秒）
PERFORMANCE_HISTORY_HOURS=24   # 歷史數據保留時間
PERFORMANCE_ALERT_ENABLED=true # 啟用警報
```

### 檔案結構
```
performance-monitor/
├── SKILL.md
├── performance_monitor.py
├── telegram_handler.py
├── config.json
├── requirements.txt
└── data/
    ├── history.db
    └── alerts.log
```

## 安裝

1. 安裝依賴：
```bash
pip install psutil matplotlib
```

2. 複製技能到技能目錄：
```bash
cp -r performance-monitor /usr/lib/node_modules/openclaw/skills/
```

3. 重啟 OpenClaw：
```bash
openclaw gateway restart
```

## 開發指南

### 添加新監控指標
1. 在 `resource_monitor.py` 中添加新的監控函數
2. 在 `dashboard.py` 中添加顯示邏輯
3. 在 `telegram_handler.py` 中添加對應的命令處理

### 自定義警報
修改 `alert_system.py` 中的閾值和條件

### 擴展數據儲存
修改 `data_store.py` 支持不同的儲存後端

## 效能考量
- 數據收集間隔可配置
- 歷史數據自動清理
- 記憶體使用優化
- 非阻塞 I/O 操作

## 故障排除

### 常見問題
1. **psutil 未安裝**：`pip install psutil`
2. **權限不足**：確保有系統監控權限
3. **數據不更新**：檢查更新間隔設置

### 日誌位置
- 系統日誌：`/var/log/openclaw/performance-monitor.log`
- 錯誤日誌：`workspace/performance-monitor/error.log`

## 版本歷史
- v1.0.0：初始版本，基礎監控功能
- v1.1.0：添加 Telegram 介面
- v1.2.0：添加警報系統
- v1.3.0：添加歷史趨勢圖

## 貢獻
歡迎提交 Pull Request 或報告問題。

## 授權
MIT License