#!/usr/bin/env python3
"""
Session 重置報告
════════════════
當 /reset 或 /new 觸發時，由 OpenClaw session-report hook 呼叫。
直接透過 Telegram API 發送：
  1. 每日開發日報（透過 dev_daily_report.py 的 build_report）
  2. 監控儀表板快照（HTML 模式）

完全不依賴 AI — 由系統層級直接發送。
"""

import json
import os
import sys
import time

import requests

# ─── 環境載入 ─────────────────────────────────────────

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
STATE_FILE = "/root/.openclaw/monitoring/monitoring_state.json"
DEDUP_FILE = "/root/.openclaw/monitoring/session_report_state.json"


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

    def pin(self, message_id: int, silent: bool = True) -> bool:
        """釘選訊息。silent=True 不發送釘選通知。"""
        try:
            r = requests.post(f"{self.base}/pinChatMessage", json={
                "chat_id": self.chat_id,
                "message_id": message_id,
                "disable_notification": silent,
            }, timeout=10)
            return r.json().get("ok", False)
        except Exception:
            return False


def _dedup_check() -> bool:
    """防止短時間內重複發送（5 秒內的重複觸發跳過）"""
    os.makedirs(os.path.dirname(DEDUP_FILE), exist_ok=True)
    now = time.time()
    try:
        if os.path.exists(DEDUP_FILE):
            with open(DEDUP_FILE) as f:
                state = json.load(f)
            last = state.get("last_sent", 0)
            if now - last < 5:
                print("⏸️ 5 秒內已發送過，跳過")
                return False
    except Exception:
        pass
    with open(DEDUP_FILE, "w") as f:
        json.dump({"last_sent": now}, f)
    return True


# ─── 報告 1：開發日報 ──────────────────────────────────

def send_dev_report(sender: TelegramSender) -> bool:
    """呼叫 dev_daily_report 的 build_report 並發送"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from dev_daily_report import build_report, load_state, save_state, TZ_GMT8
        from datetime import datetime

        report_text = build_report()
        state = load_state()
        today = datetime.now(TZ_GMT8).strftime("%Y-%m-%d")

        msg_id = state.get("message_id")
        state_date = state.get("date")

        # 同一天 → 編輯；不同天 → 新訊息
        if state_date == today and msg_id:
            try:
                r = requests.post(f"{sender.base}/editMessageText", json={
                    "chat_id": sender.chat_id, "message_id": int(msg_id),
                    "text": report_text,
                    "parse_mode": "HTML", "disable_web_page_preview": True,
                }, timeout=20)
                if not r.json().get("ok"):
                    raise RuntimeError("edit failed")
                print(f"✅ 開發日報已更新 (msg_id={msg_id})")
            except Exception:
                msg_id = sender.send(report_text)
                state["message_id"] = msg_id
                print(f"✅ 開發日報已發送 (msg_id={msg_id})")
        else:
            msg_id = sender.send(report_text)
            state["message_id"] = msg_id
            print(f"✅ 開發日報已發送 (msg_id={msg_id})")

        state["date"] = today
        save_state(state)
        return True
    except Exception as e:
        print(f"⚠️ 開發日報失敗: {e}")
        return False


# ─── 報告 2：監控面板 ──────────────────────────────────

def send_monitor_dashboard(sender: TelegramSender) -> bool:
    """讀取 monitoring_state.json 並發送 HTML 格式儀表板"""
    try:
        if not os.path.exists(STATE_FILE):
            print("⚠️ 監控狀態檔不存在，跳過")
            return False

        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from health_engine import render_dashboard

        dashboard_text = render_dashboard(state, html=True)
        msg_id = sender.send(dashboard_text)
        # 自動釘選監控面板
        if sender.pin(msg_id):
            print(f"✅ 監控面板已發送並釘選 (msg_id={msg_id})")
        else:
            print(f"✅ 監控面板已發送 (msg_id={msg_id})，釘選失敗")
        return True
    except Exception as e:
        print(f"⚠️ 監控面板失敗: {e}")
        return False


# ─── 主程式 ───────────────────────────────────────────

def main() -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未設定")
        return 1

    if not _dedup_check():
        return 0

    # 多租戶支援：如果有 tenant_manager，通知所有啟用的租戶
    chat_ids = []
    try:
        from tenant_manager import TenantManager
        tm = TenantManager()
        for tenant in tm.get_active_tenants():
            if tenant.get_setting("alerts_enabled", True):
                chat_ids.append(tenant.chat_id)
    except Exception:
        pass

    if not chat_ids:
        chat_ids.append(chat_id)

    success = 0
    for cid in chat_ids:
        sender = TelegramSender(token, cid)
        r1 = send_dev_report(sender)
        r2 = send_monitor_dashboard(sender)
        if r1 or r2:
            success += 1

    return 0 if success > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
