# Agent Monitoring System - Telegram 即時可視化監控系統

## 概述
一個用於監控 OpenClaw 代理狀態的即時可視化系統，透過 Telegram 提供 HTML 格式的儀表板。

## 功能特色
- **即時監控**: 追蹤所有活躍會話的狀態和進度
- **資源監控**: 監控 CPU、記憶體、磁碟使用情況
- **任務追蹤**: 顯示任務狀態、進度條和估計完成時間
- **Telegram 儀表板**: 使用 HTML 格式的豐富視覺化介面
- **自動更新**: 輪詢機制提供即時更新
- **警報系統**: 異常狀態自動通知

## 模組結構
```
agent-monitoring-system/
├── SKILL.md                    # 技能說明文件
├── agent_monitor.py            # 主監控類別
├── session_tracker.py          # 會話追蹤器
├── resource_monitor.py         # 資源監控器
├── telegram_dashboard.py       # Telegram 儀表板生成器
├── data_store.py              # 數據存儲
├── config.py                  # 配置管理
├── alert_system.py            # 警報系統
├── integration.py             # 系統整合
├── __init__.py               # 套件初始化
├── requirements.txt          # 依賴套件
└── test_monitoring.py        # 測試腳本
```

## 安裝與設定

### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

### 2. 設定配置
編輯 `config.py` 或建立 `.env` 檔案：
```python
# Telegram Bot 設定
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"

# 監控設定
POLLING_INTERVAL = 30  # 秒
HISTORY_RETENTION_DAYS = 7
```

### 3. 啟動監控
```python
from agent_monitor import AgentMonitor

monitor = AgentMonitor()
monitor.start()
```

## 使用方法

### 基本使用
```python
# 初始化監控系統
from agent_monitor import AgentMonitor

monitor = AgentMonitor()
monitor.start_monitoring()

# 手動更新儀表板
monitor.update_dashboard()

# 停止監控
monitor.stop()
```

### Telegram 指令
```
/monitor_status - 顯示當前監控狀態
/monitor_start - 啟動監控
/monitor_stop - 停止監控
/monitor_config - 顯示配置
```

## API 端點
- `GET /api/sessions` - 獲取所有會話狀態
- `GET /api/resources` - 獲取資源使用情況
- `GET /api/dashboard` - 獲取儀表板 HTML
- `POST /api/alert` - 觸發警報

## 整合功能
- **OpenClaw 會話管理**: 自動偵測新會話
- **議題追蹤系統**: 連結任務與議題
- **效能監控**: 系統資源使用趨勢分析

## 開發指南
1. 新增監控指標：編輯 `agent_monitor.py`
2. 自訂儀表板：編輯 `telegram_dashboard.py`
3. 新增警報規則：編輯 `alert_system.py`

## 故障排除
- **無法連接 Telegram**: 檢查 Bot Token 和 Chat ID
- **數據不更新**: 檢查 OpenClaw Gateway 狀態
- **記憶體洩漏**: 調整 `HISTORY_RETENTION_DAYS`

## 授權
MIT License