---
name: system-monitor
description: 系統監控、開發日報、費用報告、Git 操作、備份 — 直接腳本執行
metadata: {"clawdbot":{"emoji":"📊","requires":{"bins":["python3"]}}}
---

# 系統監控與直接指令

以下指令全部透過腳本直接執行，**不需要你自行組裝內容**。
執行指令 → 取得輸出 → **原封不動傳送給使用者**。
**絕對不要摘要、改寫或省略輸出內容。**

## /monitor — 系統監控儀表板

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/direct_commands.py monitor
```

## /devreport — 今日開發進度報告

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/direct_commands.py devreport
```

## /costreport — API 使用量與費用報告

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/direct_commands.py costreport
```

## /gitlog — 最近 Git 提交紀錄

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/direct_commands.py gitlog
```

## /gitdiff — 目前未提交的變更

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/direct_commands.py gitdiff
```

## /gitbranch — 分支列表

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/direct_commands.py gitbranch
```

## /quickbackup — 快速備份並推送

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/direct_commands.py quickbackup
```

## /info — 系統資訊

```bash
python3 /root/.openclaw/workspace/agent-monitoring-system/direct_commands.py info
```

## 規則

1. 收到以上任何指令時，**直接執行對應的 bash 指令**
2. 將腳本輸出**完整、原封不動**傳送給使用者
3. **不要加上任何額外說明、摘要或評論**
4. 輸出已包含完整格式（HTML 標籤），不需要額外處理
5. 如果需要最新監控資料（而非快取），先執行：
   ```bash
   cd /root/.openclaw/workspace/agent-monitoring-system && python3 health_engine.py 2>&1
   ```
   再執行 monitor 指令
