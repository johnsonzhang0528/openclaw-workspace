# OpenClaw 監控系統

## 系統概述

這是一個自動化的監控儀表板系統，用於追蹤 OpenClaw 子代理任務狀態、系統資源使用情況，並提供即時警報和 Telegram 通知。

## 系統架構

### 核心組件

1. **簡化監控儀表板** (`simple_monitoring_dashboard.py`)
   - 獲取子代理會話數據
   - 分析會話狀態（活躍、近期、歷史）
   - 獲取系統資源指標（CPU、記憶體、磁碟、負載）
   - 生成精簡儀表板
   - 更新監控狀態檔案

2. **監控服務** (`monitoring_service.py`)
   - 定期執行監控更新
   - 檢查警報條件
   - 管理 Telegram 通知
   - 提供服務控制介面（啟動/停止/狀態）

3. **監控 Cron 任務** (`monitoring_cron.py`)
   - 定期執行監控更新
   - 檢查並發送警報
   - 整點發送完整儀表板

4. **監控配置** (`monitoring_config.json`)
   - 系統配置設定
   - 警報閾值
   - 通知設定
   - 數據保留策略

5. **監控狀態** (`monitoring-state.json`)
   - 即時監控數據
   - 任務統計
   - 系統指標
   - 性能統計

## 安裝與設定

### 1. 基本設定

```bash
# 確保腳本有執行權限
chmod +x /root/.openclaw/workspace/simple_monitoring_dashboard.py
chmod +x /root/.openclaw/workspace/monitoring_service.py
chmod +x /root/.openclaw/workspace/monitoring_cron.py
```

### 2. Telegram 設定（可選）

編輯 `monitoring_config.json`：
```json
{
  "telegram_enabled": true,
  "telegram_chat_id": "YOUR_CHAT_ID"
}
```

### 3. 警報閾值設定

根據你的需求調整警報閾值：
```json
"alert_thresholds": {
  "cpu_percent": 80,
  "memory_percent": 75,
  "disk_percent": 90,
  "session_count": 20,
  "task_duration_minutes": 60,
  "stalled_minutes": 10
}
```

## 使用方法

### 手動執行監控

```bash
# 執行單次監控更新
python3 /root/.openclaw/workspace/simple_monitoring_dashboard.py

# 或使用監控服務
python3 /root/.openclaw/workspace/monitoring_service.py update
```

### 啟動監控服務

```bash
# 啟動監控服務（後台運行）
python3 /root/.openclaw/workspace/monitoring_service.py start --interval 300

# 查看服務狀態
python3 /root/.openclaw/workspace/monitoring_service.py status

# 停止服務
python3 /root/.openclaw/workspace/monitoring_service.py stop
```

### 測試監控系統

```bash
# 完整測試
python3 /root/.openclaw/workspace/monitoring_service.py test

# 啟用 Telegram 測試
python3 /root/.openclaw/workspace/monitoring_service.py test --telegram --chat-id YOUR_CHAT_ID
```

## 自動化監控

### OpenClaw Cron 任務

系統已建立每5分鐘執行一次的 cron 任務：
- 任務名稱：監控儀表板定期更新
- 執行間隔：300秒（5分鐘）
- 執行內容：更新監控狀態和儀表板

### 手動管理 Cron 任務

```bash
# 查看現有 cron 任務
openclaw cron list

# 手動執行監控任務
openclaw cron run 1dcb6dc4-aadf-4cd4-971c-9831d6e90123

# 禁用/啟用任務
openclaw cron update 1dcb6dc4-aadf-4cd4-971c-9831d6e90123 '{"enabled": false}'
```

## 監控數據

### 即時數據檔案

1. **最新儀表板**：`latest_dashboard.txt`
   - 精簡格式的監控儀表板
   - 適合 Telegram 發送

2. **監控狀態**：`monitoring-state.json`
   - 完整的監控數據
   - 任務統計和系統指標
   - 性能數據和警報狀態

3. **最新警報**：`latest_alerts.txt`
   - 當前的系統警報
   - 超過閾值的指標

### 數據結構

```json
{
  "version": "1.0",
  "last_update": "2026-02-12T14:55:07+08:00",
  "monitoring_enabled": true,
  "tasks": {
    "total": 17,
    "running": 5,
    "completed": 0,
    "failed": 0,
    "pending": 12
  },
  "system_metrics": {
    "cpu_load": 2.4,
    "memory_percent": 22.8,
    "disk_percent": 8.0,
    "load_average": [0.18, 0.16, 0.11]
  },
  "alerts": {
    "active": 0,
    "total_today": 0
  }
}
```

## 警報系統

### 警報類型

1. **資源警報**
   - CPU 使用率 > 80%
   - 記憶體使用率 > 75%
   - 磁碟使用率 > 90%

2. **任務警報**
   - 子代理會話數量 > 20
   - 任務運行時間 > 60分鐘
   - 任務停滯時間 > 10分鐘

### 通知設定

- **即時警報**：發現警報時立即通知
- **整點摘要**：每小時發送完整儀表板
- **安靜時段**：00:00-08:00 減少通知
- **週末模式**：減少通知頻率

## 故障排除

### 常見問題

1. **JSON 解析錯誤**
   ```
   ❌ JSON 解析錯誤: Unterminated string in JSON at position 17268
   ```
   **解決方案**：使用 `simple_monitoring_dashboard.py` 中的 JSON 修復功能

2. **OpenClaw 命令超時**
   ```
   ❌ 命令執行超時
   ```
   **解決方案**：增加 timeout 設定或檢查 OpenClaw 服務狀態

3. **Telegram 發送失敗**
   ```
   ❌ 發送到 Telegram 失敗
   ```
   **解決方案**：檢查 Telegram Bot Token 和 Chat ID 設定

### 日誌檢查

```bash
# 查看監控服務日誌
tail -f /root/.openclaw/workspace/monitoring.log

# 檢查系統資源
top -bn1 | head -20
free -h
df -h /
```

## 擴展功能

### 自定義監控

1. **添加新的監控指標**
   - 修改 `simple_monitoring_dashboard.py` 中的 `get_system_metrics()` 函數
   - 添加新的系統命令或 API 調用

2. **自定義警報規則**
   - 編輯 `monitoring_config.json` 中的 `alert_thresholds`
   - 在 `monitoring_service.py` 中添加新的警報檢查

3. **集成其他通知管道**
   - 添加 Email、Slack、Discord 等通知支援
   - 修改 `send_to_telegram()` 函數或添加新的發送函數

### 性能優化

1. **緩存機制**
   - 監控數據緩存 30 秒
   - 減少 OpenClaw CLI 調用頻率

2. **批量處理**
   - 多個監控檢查合併執行
   - 減少系統負載

3. **智能調度**
   - 根據系統負載調整監控頻率
   - 安靜時段減少監控

## 維護與更新

### 定期維護

1. **清理舊數據**
   ```bash
   # 清理7天前的儀表板歷史
   find /root/.openclaw/workspace -name "dashboard_*.txt" -mtime +7 -delete
   
   # 清理30天前的警報歷史
   find /root/.openclaw/workspace -name "alerts_*.txt" -mtime +30 -delete
   ```

2. **更新配置**
   ```bash
   # 備份當前配置
   cp /root/.openclaw/workspace/monitoring_config.json /root/.openclaw/workspace/monitoring_config.json.backup
   
   # 更新配置後重啟服務
   python3 /root/.openclaw/workspace/monitoring_service.py stop
   python3 /root/.openclaw/workspace/monitoring_service.py start
   ```

### 版本升級

1. **備份當前系統**
   ```bash
   # 備份所有監控相關檔案
   tar -czf monitoring_backup_$(date +%Y%m%d).tar.gz \
     /root/.openclaw/workspace/simple_monitoring_dashboard.py \
     /root/.openclaw/workspace/monitoring_service.py \
     /root/.openclaw/workspace/monitoring_cron.py \
     /root/.openclaw/workspace/monitoring_config.json \
     /root/.openclaw/workspace/monitoring-state.json
   ```

2. **更新腳本**
   ```bash
   # 下載最新版本
   wget -O /root/.openclaw/workspace/simple_monitoring_dashboard.py.new \
     https://example.com/latest/simple_monitoring_dashboard.py
   
   # 測試新版本
   python3 /root/.openclaw/workspace/simple_monitoring_dashboard.py.new
   
   # 替換舊版本
   mv /root/.openclaw/workspace/simple_monitoring_dashboard.py.new \
     /root/.openclaw/workspace/simple_monitoring_dashboard.py
   ```

## 聯絡與支援

如有問題或建議，請聯繫系統管理員或查看 OpenClaw 官方文檔。

---

**最後更新**：2026-02-12  
**版本**：1.0.0  
**狀態**：運行中 ✅