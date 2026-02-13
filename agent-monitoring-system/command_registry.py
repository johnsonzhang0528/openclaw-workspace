#!/usr/bin/env python3
"""
統一指令註冊表 (Unified Command Registry)
═══════════════════════════════════════════
所有 Telegram 斜線指令的 **唯一定義來源**。

分類：
  MONITOR_COMMANDS  — 監控系統指令 → menu_handler.py 處理（HTML 輸出）
  OPENCLAW_COMMANDS — OpenClaw AI 指令 → AI 代理處理（純文字輸出）

規則：
  ★ 兩組指令名稱不得重複
  ★ 新增 / 修改指令只需編輯此檔案
  ★ health_engine 啟動時自動同步到 openclaw.json
"""

import json
import os
from typing import List, Dict

# ─── 監控系統指令（menu_handler.py 處理）────────────────

MONITOR_COMMANDS: List[Dict[str, str]] = [
    {"command": "menu",    "description": "📱 開啟主控面板"},
    {"command": "monitor", "description": "📊 系統監控儀表板"},
    {"command": "token",   "description": "💰 Token 成本摘要"},
    {"command": "backup",  "description": "💾 備份狀態"},
    {"command": "config",  "description": "⚙️ 查看設定"},
    {"command": "logs",    "description": "📝 磁碟使用報告"},
    {"command": "info",    "description": "ℹ️ 系統資訊"},
    {"command": "help",    "description": "❓ 指令說明"},
]

# ─── OpenClaw AI 指令（由 AI 代理處理）────────────────────

OPENCLAW_COMMANDS: List[Dict[str, str]] = [
    {"command": "issue",         "description": "建立新 Issue — 輸入 /issue <標題>"},
    {"command": "issuehistory",  "description": "查看最近 Issue 歷史紀錄"},
    {"command": "tasks",         "description": "列出目前進行中的任務"},
    {"command": "gitlog",        "description": "查看最近 Git 提交紀錄"},
    {"command": "gitdiff",       "description": "查看目前未提交的變更"},
    {"command": "gitbranch",     "description": "查看分支列表與目前分支"},
    {"command": "gitpush",       "description": "推送最新提交到遠端"},
    {"command": "devreport",     "description": "生成今日開發進度報告"},
    {"command": "costreport",    "description": "查看 API 使用量與費用報告"},
    {"command": "switchdev",     "description": "切換到開發 (dev) 工作階段"},
    {"command": "switchops",     "description": "切換到維運 (ops) 工作階段"},
    {"command": "switchdefault", "description": "切換回預設工作階段"},
    {"command": "quickbackup",   "description": "快速備份設定並推送到 GitHub"},
]

# ─── 全量合併 ────────────────────────────────────────────

ALL_COMMANDS: List[Dict[str, str]] = MONITOR_COMMANDS + OPENCLAW_COMMANDS


# ─── 驗證 ────────────────────────────────────────────────

def validate() -> None:
    """驗證無重複指令名。啟動時自動呼叫。"""
    names = [c["command"] for c in ALL_COMMANDS]
    seen = set()
    for n in names:
        if n in seen:
            raise ValueError(f"❌ command_registry: 指令名重複 → /{n}")
        seen.add(n)


def sync_openclaw_json(json_path: str = None) -> bool:
    """
    將 OPENCLAW_COMMANDS 同步寫入 openclaw.json 的
    channels.telegram.customCommands，確保定義一致。

    Returns:
        True = 有變更並已寫入, False = 無需變更
    """
    if json_path is None:
        json_path = os.path.join(os.path.expanduser("~"), ".openclaw", "openclaw.json")

    if not os.path.exists(json_path):
        return False

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        tg = config.get("channels", {}).get("telegram", {})
        current = tg.get("customCommands", [])

        # 比較：順序與內容完全一致則跳過
        if current == OPENCLAW_COMMANDS:
            return False

        tg["customCommands"] = OPENCLAW_COMMANDS
        config.setdefault("channels", {}).setdefault("telegram", {})
        config["channels"]["telegram"] = tg

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"🔄 command_registry: 已同步 {len(OPENCLAW_COMMANDS)} 個 AI 指令至 openclaw.json")
        return True
    except Exception as e:
        print(f"⚠️ command_registry: 同步 openclaw.json 失敗: {e}")
        return False


# ─── 骨架佔位定義（skeleton message）──────────────────────
#
# 供 menu_handler.py 使用。key = 指令名或 (page, action) tuple。
# value = (icon, title)

SKELETON_SLASH: Dict[str, tuple] = {
    "/monitor": ("📊", "系統監控儀表板"),
    "/token":   ("💰", "Token 成本摘要"),
    "/backup":  ("💾", "備份狀態"),
    "/config":  ("⚙️", "系統設定"),
    "/logs":    ("📝", "磁碟報告"),
    "/info":    ("ℹ️", "系統資訊"),
}

SKELETON_CALLBACK: Dict[tuple, tuple] = {
    # 監控中心
    ("mon", "dash"):    ("📊", "健康儀表板"),
    ("mon", "perf"):    ("📈", "效能詳情"),
    ("mon", "alerts"):  ("⚠️", "最近告警"),
    # 系統操作
    ("sys", "logs"):    ("📋", "Gateway 日誌"),
    ("sys", "health"):  ("🩺", "健康檢查"),
    # 備份管理
    ("bak", "status"):  ("📊", "備份狀態"),
    ("bak", "list"):    ("📋", "備份列表"),
    # 設定管理
    ("cfg", "view"):    ("📋", "系統設定"),
    ("cfg", "history"): ("📜", "變更紀錄"),
    # 日誌報告
    ("log", "disk"):    ("📊", "磁碟報告"),
    # Token 成本
    ("tok", "summary"): ("💰", "成本摘要"),
    ("tok", "detail"):  ("📊", "費用詳情"),
    ("tok", "hourly"):  ("⏰", "24h 分佈"),
    ("tok", "budget"):  ("💳", "預算狀態"),
    # 系統資訊
    ("info", ""):       ("ℹ️", "系統資訊"),
}


def skeleton_text(icon: str, title: str) -> str:
    """產生骨架佔位 HTML 文字。"""
    return f"<b>{icon} {title}</b>\n{'━' * 25}\n\n⏳ 資料載入中..."


# 模組載入時自動驗證
validate()
