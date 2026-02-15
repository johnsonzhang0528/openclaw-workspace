#!/usr/bin/env python3
"""
發送 Gateway 重啟完成通知
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import requests

TZ_GMT8 = timezone(timedelta(hours=8))
ENV_FILE = "/root/.openclaw/workspace/agent-monitoring-system/.env"
STATE_FILE = "/root/.openclaw/monitoring/gateway_restart_state.json"


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
        return {"last_restart_time": None}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def get_gateway_start_time() -> datetime:
    """取得 Gateway 啟動時間"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", "openclaw-gateway", "--property=ActiveEnterTimestamp"],
            capture_output=True, text=True, timeout=10,
        )
        line = result.stdout.strip()
        if not line or "=" not in line:
            return None
        timestamp_str = line.split("=", 1)[1].strip()
        if not timestamp_str or timestamp_str == "n/a":
            return None
        
        # 解析時間 (移除時區縮寫)
        timestamp_str = " ".join(timestamp_str.split()[:-1])
        return datetime.strptime(timestamp_str, "%a %Y-%m-%d %H:%M:%S")
    except Exception:
        return None


class TelegramSender:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def send(self, text: str, keyboard: list = None, pin: bool = False) -> int:
        payload = {
            "chat_id": self.chat_id, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }
        if keyboard:
            payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
        try:
            r = requests.post(f"{self.base}/sendMessage", json=payload, timeout=20)
            r.raise_for_status()
            msg_id = int(r.json()["result"]["message_id"])
            if pin:
                self._pin(msg_id)
            return msg_id
        except Exception as exc:
            print(f"⚠️ Telegram send failed: {exc}")
            return 0

    def _pin(self, message_id: int):
        try:
            requests.post(
                f"{self.base}/pinChatMessage",
                json={"chat_id": self.chat_id, "message_id": message_id,
                      "disable_notification": True},
                timeout=10,
            )
        except Exception:
            pass


# ─── Post-reset 自動推送 ────────────────────────────────

def _send_owner_post_reset(sender: TelegramSender, tm, tenant):
    """
    Owner 專屬 post-reset 推送（按順序）：
      1. 監控儀表板（pinned）
      2. 開發日報
      3. 費用日報
      4. 主控面板
    """
    state = tm.load_tenant_state(tenant)

    # 1. 監控儀表板（pinned）
    try:
        from health_engine import render_dashboard
        dashboard_text = render_dashboard(state)
        msg_id = sender.send(dashboard_text, pin=True)
        if msg_id:
            state["dashboard_message_id"] = msg_id
            tm.save_tenant_state(tenant, state)
            print(f"📊 儀表板已推送並釘選 (msg_id={msg_id})")
    except Exception as e:
        print(f"⚠️ 儀表板推送失敗: {e}")

    # 2. 開發日報
    try:
        from dev_daily_report import build_report
        report = build_report()
        if report:
            sender.send(report)
            print("📋 開發日報已推送")
    except Exception as e:
        print(f"⚠️ 開發日報推送失敗: {e}")

    # 3. 費用日報
    try:
        from usage_cost_report import get_openclaw_usage, calculate_cost, build_usage_report
        usage = get_openclaw_usage()
        cost = calculate_cost(usage)
        history = []  # post-reset 不帶歷史
        report = build_usage_report(usage, cost, history)
        if report:
            sender.send(report)
            print("💰 費用日報已推送")
    except Exception as e:
        print(f"⚠️ 費用日報推送失敗: {e}")

    # 4. 主控面板
    _send_menu(sender, state)


def _send_tenant_post_reset(sender: TelegramSender, tm, tenant):
    """
    一般租戶 post-reset 推送：
      1. 主控面板（pinned）
    """
    state = tm.load_tenant_state(tenant)
    _send_menu(sender, state, pin=True)


def _send_menu(sender: TelegramSender, state: dict, pin: bool = False):
    """推送主控面板（含 inline keyboard）"""
    try:
        from telegram_ui import page_home, kb_main_menu
        score = state.get("health_score", 0)
        grade = state.get("health_grade", "?")
        ts = state.get("last_updated", "")
        msg_id = sender.send(page_home(score, grade, ts), keyboard=kb_main_menu(), pin=pin)
        if msg_id:
            action = "釘選" if pin else ""
            print(f"📱 主控面板已推送{action} (msg_id={msg_id})")
    except Exception as e:
        print(f"⚠️ 主控面板推送失敗: {e}")


def main() -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN 未設定")
        return 1

    # 取得 Gateway 啟動時間
    start_time = get_gateway_start_time()
    if not start_time:
        print("❌ 無法取得 Gateway 啟動時間")
        return 1

    # 檢查是否為新的重啟（距離上次通知超過 30 秒）
    state = load_state()
    last_restart = state.get("last_restart_time")
    
    now = datetime.now()
    uptime = (now - start_time).total_seconds()
    
    # 只有在啟動時間少於 120 秒時才發送通知（表示是剛重啟的）
    if uptime > 120:
        print(f"⏸️ Gateway 已運行 {uptime:.0f} 秒，不是新重啟，跳過通知")
        return 0
    
    # 如果上次通知時間與本次啟動時間相同，跳過（避免重複通知）
    start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    if last_restart == start_time_str:
        print(f"⏸️ 此次重啟已通知過，跳過")
        return 0
    
    # ── 多租戶：通知所有啟用的租戶（區分 owner 與一般用戶）──
    tm = None
    rbac_mod = None
    tenants = []
    owner_chat_id = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tenant_manager import TenantManager
        tm = TenantManager()
        tenants = [t for t in tm.get_active_tenants() if t.get_setting("alerts_enabled", True)]

        # 取得 owner chat_id（RBAC 中角色為 owner 的用戶）
        try:
            from rbac import RBACManager
            rbac_mod = RBACManager()
            for t in tenants:
                tid = t.tenant_id
                tenant_roles = rbac_mod._roles.get(tid, {})
                for uid, user_role in tenant_roles.items():
                    if user_role.role == "owner":
                        owner_chat_id = t.chat_id
                        break
                if owner_chat_id:
                    break
        except Exception:
            pass

        # 回退：找不到 owner 時，第一個租戶視為 owner
        if not owner_chat_id and tenants:
            owner_chat_id = tenants[0].chat_id

    except Exception as e:
        print(f"⚠️ 載入租戶失敗: {e}")

    # 回退：無租戶時用 .env
    if not tenants:
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not chat_id:
            print("❌ 無可通知的租戶")
            return 1
        # 單租戶模式 — 視為 owner
        now_gmt8 = datetime.now(TZ_GMT8)
        s = TelegramSender(token, chat_id)
        s.send(
            f"✅ <b>Gateway 重啟完成</b>\n"
            f"{'━' * 25}\n"
            f"狀態: 🟢 運行中\n"
            f"完成時間: {now_gmt8.strftime('%Y-%m-%d %H:%M:%S')} GMT+8\n"
            f"啟動耗時: 約 {uptime:.1f} 秒"
        )
        state["last_restart_time"] = start_time_str
        save_state(state)
        return 0

    now_gmt8 = datetime.now(TZ_GMT8)
    restart_text = (
        f"✅ <b>Gateway 重啟完成</b>\n"
        f"{'━' * 25}\n"
        f"狀態: 🟢 運行中\n"
        f"完成時間: {now_gmt8.strftime('%Y-%m-%d %H:%M:%S')} GMT+8\n"
        f"啟動耗時: 約 {uptime:.1f} 秒"
    )

    sent_count = 0
    for tenant in tenants:
        try:
            sender = TelegramSender(token, tenant.chat_id)
            # 先發重啟通知
            sender.send(restart_text)
            sent_count += 1

            # Post-reset 自動推送（依角色區分）
            if tenant.chat_id == owner_chat_id:
                _send_owner_post_reset(sender, tm, tenant)
            else:
                _send_tenant_post_reset(sender, tm, tenant)

            print(f"✅ 已完成 post-reset 推送至 {tenant.chat_id}")
        except Exception as e:
            print(f"⚠️ 推送至 {tenant.chat_id} 失敗: {e}")

    if sent_count > 0:
        state["last_restart_time"] = start_time_str
        save_state(state)

    return 0 if sent_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
