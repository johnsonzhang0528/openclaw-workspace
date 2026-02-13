# BOOT.md — 啟動清單

每次 Gateway 啟動或 session 重置後，依序執行以下步驟：

## 1. 發送開發日報

執行以下命令生成並發送今日開發進度報告：

```bash
cd /root/.openclaw/workspace/agent-monitoring-system && python3 dev_daily_report.py
```

## 2. 發送監控面板

執行以下命令取得最新監控快照，並將結果發送給使用者：

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/monitor_snapshot.py
```

將輸出內容直接展示給使用者。

## 3. 簡短問候

完成上述步驟後，用一句話告知使用者系統狀態已就緒，例如：
> 「系統已就緒，以上是今日開發日報與監控面板。」

---

_注意：不要跳過任何步驟，不要詢問使用者是否需要執行。直接執行。_
