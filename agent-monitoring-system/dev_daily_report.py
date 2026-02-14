#!/usr/bin/env python3
"""
每日開發進度報告 — 每天 08:00 (GMT+8) 自動生成
使用「編輯同一則訊息」模式，全天只維護一則訊息
"""

import json
import os
import subprocess
import sys
from html import escape as _esc
from datetime import datetime, timezone, timedelta

import requests

TZ_GMT8 = timezone(timedelta(hours=8))
STATE_FILE = "/root/.openclaw/monitoring/dev_daily_report_state.json"
ENV_FILE = "/root/.openclaw/workspace/agent-monitoring-system/.env"
WORKSPACE = "/root/.openclaw/workspace"
CONFIG_DIR = "/root/.openclaw"


def load_env() -> None:
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def load_state() -> dict:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    if not os.path.exists(STATE_FILE):
        return {"message_id": None, "date": None}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ─── Git 統計 ───────────────────────────────────────────────

def git_today_commits(repo_path: str) -> list[dict]:
    """取得今天 (GMT+8) 的 git commit"""
    now = datetime.now(TZ_GMT8)
    since = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        result = subprocess.run(
            ["git", "--no-pager", "log", f"--since={since}", "--pretty=format:%h|%s|%ai", "--no-merges"],
            capture_output=True, text=True, timeout=15, cwd=repo_path,
        )
        if result.returncode != 0:
            return []
        commits = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"hash": parts[0], "msg": parts[1], "time": parts[2]})
        return commits
    except Exception:
        return []


def git_stat_today(repo_path: str) -> dict:
    """取得今天的變更統計"""
    now = datetime.now(TZ_GMT8)
    since = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        result = subprocess.run(
            ["git", "--no-pager", "diff", "--shortstat", f"HEAD@{{{since}}}"],
            capture_output=True, text=True, timeout=15, cwd=repo_path,
        )
        return {"stat": result.stdout.strip() or "無變更"}
    except Exception:
        return {"stat": "無法取得"}


def git_branch_info(repo_path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=10, cwd=repo_path,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def git_uncommitted_count(repo_path: str) -> int:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, cwd=repo_path,
        )
        return len([l for l in result.stdout.strip().splitlines() if l.strip()])
    except Exception:
        return 0


# ─── Session 統計 ──────────────────────────────────────────

def get_session_stats() -> dict:
    """讀取 monitoring state 取得今天的 session 統計"""
    monitor_state_file = "/root/.openclaw/monitoring/unified_dashboard_state.json"
    if not os.path.exists(monitor_state_file):
        return {"today": 0, "completed": 0, "failed": 0, "avg_min": 0.0}
    try:
        with open(monitor_state_file, "r") as f:
            data = json.load(f)
        h = data.get("history", {})
        completed = h.get("completed_sessions", 0)
        return {
            "today": h.get("today_sessions", 0),
            "completed": completed,
            "failed": h.get("failed_sessions", 0),
            "avg_min": round(h.get("total_runtime_minutes", 0) / max(completed, 1), 1),
        }
    except Exception:
        return {"today": 0, "completed": 0, "failed": 0, "avg_min": 0.0}


# ─── 系統資源快照 ──────────────────────────────────────────

def sys_snapshot() -> dict:
    def sh(cmd: str) -> str:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception:
            return "N/A"

    return {
        "cpu": sh("top -bn1 | grep 'Cpu(s)' | awk '{printf \"%.1f%%\", $2}'"),
        "mem": sh("free -h | awk '/Mem:/{printf \"%s / %s (%.0f%%)\", $3, $2, $3/$2*100}'"),
        "disk": sh("df -h / | tail -1 | awk '{printf \"%s / %s (%s)\", $3, $2, $5}'"),
        "uptime": sh("uptime -p"),
        "load": sh("cat /proc/loadavg | awk '{print $1, $2, $3}'"),
    }


# ─── Gateway 狀態 ─────────────────────────────────────────

def gateway_status() -> str:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "openclaw-gateway"],
            capture_output=True, text=True, timeout=10,
        )
        status = result.stdout.strip()
        return "🟢 運行中" if status == "active" else f"🔴 {status}"
    except Exception:
        return "❓ 無法偵測"


# ─── 報告生成 ──────────────────────────────────────────────

def build_report() -> str:
    now = datetime.now(TZ_GMT8)
    sections = []

    # Header
    sections.append(
        f"<b>📋 每日開發進度報告</b>\n"
        f"<code>{now.strftime('%Y-%m-%d (%A)')} · {now.strftime('%H:%M')} GMT+8</code>\n"
        f"{'━' * 30}"
    )

    # Git — Workspace
    ws_branch = git_branch_info(WORKSPACE)
    ws_commits = git_today_commits(WORKSPACE)
    ws_uncommitted = git_uncommitted_count(WORKSPACE)

    git_section = f"\n<b>📂 Workspace</b>  <code>{ws_branch}</code>\n"
    if ws_commits:
        git_section += f"提交: <b>{len(ws_commits)}</b> 筆\n"
        for c in ws_commits[:5]:
            git_section += f"  <code>{c['hash']}</code> {_esc(c['msg'][:50])}\n"
        if len(ws_commits) > 5:
            git_section += f"  ...另有 {len(ws_commits) - 5} 筆\n"
    else:
        git_section += "提交: 0 筆\n"
    if ws_uncommitted:
        git_section += f"未提交: <b>{ws_uncommitted}</b> 個檔案"
    sections.append(git_section)

    # Git — Config
    cfg_branch = git_branch_info(CONFIG_DIR)
    cfg_commits = git_today_commits(CONFIG_DIR)
    cfg_uncommitted = git_uncommitted_count(CONFIG_DIR)

    cfg_section = f"\n<b>⚙️ Config</b>  <code>{cfg_branch}</code>\n"
    if cfg_commits:
        cfg_section += f"提交: <b>{len(cfg_commits)}</b> 筆\n"
        for c in cfg_commits[:3]:
            cfg_section += f"  <code>{c['hash']}</code> {_esc(c['msg'][:50])}\n"
    else:
        cfg_section += "提交: 0 筆\n"
    if cfg_uncommitted:
        cfg_section += f"未提交: <b>{cfg_uncommitted}</b> 個檔案"
    sections.append(cfg_section)

    # Footer
    sections.append(
        f"\n{'━' * 30}\n"
        f"<code>下次自動更新: 明日 08:00</code>"
    )

    text = "\n".join(sections)
    if len(text) > 3900:
        text = text[:3850] + "\n<code>...內容過長已截斷</code>"
    return text


# ─── Telegram 傳送 ────────────────────────────────────────

class TelegramSender:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def send(self, text: str) -> int:
        r = requests.post(f"{self.base}/sendMessage", json={
            "chat_id": self.chat_id, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }, timeout=20)
        r.raise_for_status()
        return int(r.json()["result"]["message_id"])

    def edit(self, mid: int, text: str) -> bool:
        r = requests.post(f"{self.base}/editMessageText", json={
            "chat_id": self.chat_id, "message_id": mid, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }, timeout=20)
        return r.json().get("ok", False)


# ─── 主程式 ───────────────────────────────────────────────

def main() -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未設定")
        return 1

    state = load_state()
    today = datetime.now(TZ_GMT8).strftime("%Y-%m-%d")

    report_text = build_report()
    sender = TelegramSender(token, chat_id)

    msg_id = state.get("message_id")
    state_date = state.get("date")

    # 同一天 → 編輯；不同天 → 新訊息
    if state_date == today and msg_id:
        try:
            ok = sender.edit(int(msg_id), report_text)
            if not ok:
                raise RuntimeError("edit failed")
        except Exception:
            msg_id = sender.send(report_text)
            state["message_id"] = msg_id
    else:
        msg_id = sender.send(report_text)
        state["message_id"] = msg_id

    state["date"] = today
    save_state(state)
    print(f"✅ Dev daily report sent/updated (msg_id={msg_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
