# Agent Monitoring System

Telegram 介面的即時可視化監控系統 for OpenClaw

## 功能特色

- 📊 **即時監控儀表板**：HTML 格式 Telegram 訊息
- 🚨 **智能警報系統**：閾值檢測與自動通知
- 🔄 **會話狀態追蹤**：OpenClaw 主代理與子代理進度
- 📈 **資源使用監控**：CPU、記憶體、磁碟、網路
- 🔗 **系統整合**：議題追蹤 + OpenClaw API
- 💾 **數據持久化**：SQLite 存儲歷史數據

## 系統架構

```
agent-monitoring-system/
├── config.py              # 配置管理
├── data_store.py          # SQLite 數據存儲
├── session_tracker.py     # 會話狀態追蹤
├── resource_monitor.py    # 資源使用監控
├── telegram_dashboard.py  # Telegram 儀表板
├── alert_system.py        # 警報系統
├── agent_monitor.py       # 主監控類別
├── integration.py         # 系統整合
├── test_monitoring.py     # 測試腳本
├── __init__.py           # 套件初始化
├── setup.py              # 安裝設定
├── requirements.txt      # 依賴套件
├── .env.example         # 環境變數範例
└── README.md            # 說明文件
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

複製 `.env.example` 為 `.env` 並修改設定：

```bash
cp .env.example .env
```

編輯 `.env` 檔案：

```env
# Telegram 配置
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_DISABLE_NOTIFICATION=false

# 監控配置
MONITORING_POLLING_INTERVAL=30
MONITORING_HISTORY_RETENTION_DAYS=7
MONITORING_CPU_THRESHOLD=80
MONITORING_MEMORY_THRESHOLD=85
MONITORING_DISK_THRESHOLD=90

# 儀表板配置
DASHBOARD_COMPACT_MODE=false
DASHBOARD_UPDATE_INTERVAL=30

# 警報配置
ALERT_ENABLE_EMAIL_ALERTS=false
ALERT_ENABLE_SMS_ALERTS=false

# 整合配置
INTEGRATION_ENABLE_ISSUE_TRACKER=true
INTEGRATION_ENABLE_OPENCLAW_SESSIONS=true
```

### 3. 運行測試

```bash
# 快速冒煙測試
python test_monitoring.py quick

# 完整功能測試
python test_monitoring.py

# 測試特定模組
python test_monitoring.py module config
```

### 4. 啟動監控系統

```bash
# 直接運行
python -c "from agent_monitor import AgentMonitor; monitor = AgentMonitor(); monitor.start()"

# 或使用入口點
python agent_monitor.py
```

## 使用方式

### 基本監控

```python
from agent_monitor import AgentMonitor

# 創建監控器
monitor = AgentMonitor()

# 啟動監控
monitor.start()

# 監控系統將自動：
# 1. 每30秒更新數據
# 2. 檢查警報規則
# 3. 發送Telegram通知
# 4. 記錄歷史數據
```

### Telegram 儀表板

系統會自動生成 HTML 格式的 Telegram 訊息：

```
🤖 OpenClaw Agent 監控儀表板
最後更新: 2026-02-12 11:30:45
===================================

📈 系統資源監控
──────────────────────────────
🟢 CPU: 45.5/100 (45.5%)
🟢 記憶體: 67.8/100 (67.8%)
🟢 磁碟: 32.1/100 (32.1%)
🌐 網路: ↑125.4MB ↓89.7MB

🤖 活動會話 (3/15)
──────────────────────────────
🟢 數據分析任務 [abc123de]
├─ 📊 狀態: ACTIVE
├─ ⏱️ 運行時間: 00:45:30
├─ 🎯 進度: [████████░░░░░░░░░░░░] 40.0%
└─ ⏳ 預計完成: 1小時15分鐘後
```

### 警報系統

預設警報規則：
- CPU 使用率 > 80%：警告
- CPU 使用率 > 95%：嚴重
- 記憶體使用率 > 85%：警告
- 記憶體使用率 > 95%：嚴重
- 磁碟使用率 > 90%：警告
- 活動會話 > 20：警告

### 自定義警報規則

```python
from alert_system import AlertRule, AlertLevel

# 創建自定義規則
custom_rule = AlertRule(
    name="custom_cpu_alert",
    condition="cpu_percent>75",
    level=AlertLevel.WARNING,
    message_template="⚠️ CPU 使用率偏高: {cpu_percent:.1f}%",
    cooldown_seconds=300
)

# 添加到警報系統
alert_system.add_rule(custom_rule)
```

## 配置說明

### 監控配置 (`config.py`)

```python
@dataclass
class MonitoringConfig:
    polling_interval: int = 30  # 監控間隔（秒）
    history_retention_days: int = 7  # 歷史數據保留天數
    cpu_threshold: float = 80.0  # CPU 警告閾值
    memory_threshold: float = 85.0  # 記憶體警告閾值
    disk_threshold: float = 90.0  # 磁碟警告閾值
```

### Telegram 配置

```python
@dataclass  
class TelegramConfig:
    bot_token: str = ""  # Telegram Bot Token
    chat_id: str = ""  # 聊天 ID
    disable_notification: bool = False  # 是否禁用通知
```

## API 參考

### SessionTracker

```python
# 獲取所有會話
sessions = session_tracker.get_all_sessions()

# 獲取活動會話
active_sessions = session_tracker.get_active_sessions()

# 獲取會話統計
stats = session_tracker.get_session_stats()

# 更新會話進度
session_tracker.update_session_progress(session_id, progress)
```

### ResourceMonitor

```python
# 獲取當前資源指標
metrics = resource_monitor.get_current_metrics()

# 獲取歷史數據
history = resource_monitor.get_history(limit=100)

# 獲取系統信息
system_info = resource_monitor.get_system_info()
```

### TelegramDashboard

```python
# 生成完整儀表板
dashboard = telegram_dashboard.generate_full_dashboard()

# 生成精簡儀表板
compact_dashboard = telegram_dashboard.generate_compact_dashboard()

# 生成會話詳細資訊
session_detail = telegram_dashboard.generate_session_detail(session_id)
```

## 開發指南

### 添加新模組

1. 在套件目錄中創建新的 Python 檔案
2. 在 `__init__.py` 中導出類別和函數
3. 在 `test_monitoring.py` 中添加測試案例
4. 更新 `setup.py` 中的依賴關係

### 測試開發

```bash
# 運行所有測試
python test_monitoring.py

# 運行特定模組測試
python test_monitoring.py module alert_system

# 快速冒煙測試
python test_monitoring.py quick
```

### 代碼風格

- 使用繁體中文註解
- 遵循 PEP 8 規範
- 使用類型提示
- 添加完整的文檔字串

## 故障排除

### 常見問題

1. **導入錯誤**：確保在正確的目錄中運行，或設置 `PYTHONPATH`
2. **Telegram 通知失敗**：檢查 Bot Token 和 Chat ID 設定
3. **數據庫錯誤**：檢查 SQLite 檔案權限
4. **資源監控失敗**：檢查系統權限和依賴套件

### 日誌記錄

系統會將錯誤和重要事件記錄到標準輸出，可以重定向到檔案：

```bash
python agent_monitor.py > monitor.log 2>&1
```

## 貢獻指南

1. Fork 專案
2. 創建功能分支
3. 提交更改
4. 推送到分支
5. 創建 Pull Request

## 授權

MIT License

## 聯繫方式

- 問題回報：GitHub Issues
- 功能請求：GitHub Discussions
- 電子郵件：team@openclaw.ai

## 版本歷史

### v1.0.0 (2026-02-12)
- 初始版本發布
- 完整的監控系統功能
- Telegram 儀表板整合
- 智能警報系統
- 系統整合模組