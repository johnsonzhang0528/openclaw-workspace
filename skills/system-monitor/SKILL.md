---
name: system-monitor
description: 查看系統健康狀態、資源使用率、Gateway 運行狀況
metadata: {"clawdbot":{"emoji":"📊","requires":{"bins":["python3"]}}}
---

# 系統監控

當使用者要求查看系統狀態、監控資訊、健康檢查、/monitor 時使用。

## 快速查詢（<50ms，讀取快取）

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/monitor_snapshot.py
```

回傳最近一次採集的儀表板（每 30 秒由 cron 更新）。
直接將輸出內容展示給使用者即可。

## 強制立即採集（需要最新資料時）

```bash
cd /root/.openclaw/workspace/agent-monitoring-system && python3 health_engine.py 2>&1
python3 /root/.openclaw/workspace/agent-monitoring-system/monitor_snapshot.py
```

## 查看錯誤紀錄

```bash
tail -20 /root/.openclaw/monitoring/error_events.jsonl 2>/dev/null
```

## 查看健康分數歷史

```bash
python3 -c "
import json
with open('/root/.openclaw/monitoring/monitoring_state.json') as f:
    s = json.load(f)
print(f'健康分數: {s[\"health_score\"]}/100 ({s[\"health_grade\"]})')
print(f'更新時間: {s[\"last_updated\"]}')
print(f'Gateway: {\"運行中\" if s[\"snapshot\"][\"gateway_active\"] else \"停止\"}'  )
print(f'CPU: {s[\"snapshot\"][\"cpu_percent\"]:.1f}%')
print(f'RAM: {s[\"snapshot\"][\"memory_percent\"]:.1f}%')
print(f'Disk: {s[\"snapshot\"][\"disk_percent\"]:.1f}%')
print(f'今日錯誤: {s.get(\"errors\",{}).get(\"today_count\",0)} 筆')
"
```

## 注意

- 儀表板輸出包含 HTML 標籤（`<b>`, `<code>`），可在 Telegram 中直接傳送
- 監控狀態檔案: `/root/.openclaw/monitoring/monitoring_state.json`
- 採集間隔: 30 秒 (cron)
- 告警會自動推送到 Telegram，不需要手動觸發
