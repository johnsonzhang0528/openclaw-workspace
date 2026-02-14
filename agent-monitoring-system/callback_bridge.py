#!/usr/bin/env python3
"""
Gateway Callback Bridge — 由 Gateway 直接呼叫的 callback 處理腳本
═══════════════════════════════════════════════════════════════════
Gateway 攔截到 inline button callback 時，不送 AI，改為 spawn 此腳本。
腳本直接呼叫 menu_handler 處理，實現即時回應。

用法（由 Gateway 的 Node.js child_process.spawn 呼叫）：
  python3 callback_bridge.py '<callback_query_json>'

架構：
  Gateway (getUpdates) → 攔截 callback_query
    → m: 或 / 前綴 → spawn callback_bridge.py（即時處理）
    → commands_page_* / mdl_* → Gateway 自己處理
    → 其他 → synthetic message → AI
"""

import json
import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

ENV_FILE = os.path.join(BASE_DIR, ".env")


def load_env():
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


def main():
    if len(sys.argv) < 2:
        print("Usage: callback_bridge.py '<callback_query_json>'", file=sys.stderr)
        return 1

    load_env()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1

    try:
        cq = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return 1

    cb_data = cq.get("data", "")
    cb_id = cq.get("id", "")

    # 建立 sender（與 health_engine 相同的 TelegramSender）
    from health_engine import TelegramSender
    sender = TelegramSender(token, chat_id)

    # 載入 RBAC / TenantManager / State
    from rbac import RBACManager
    from tenant_manager import TenantManager

    rbac = RBACManager()
    tm = TenantManager()

    # 讀取主租戶 state
    tenants = tm.get_active_tenants()
    if not tenants:
        sender.answer_callback(cb_id, "❌ 無活躍租戶")
        return 1

    state = tm.load_tenant_state(tenants[0])

    # 路由
    if cb_data.startswith("m:"):
        try:
            from menu_handler import handle_menu_callback
            handle_menu_callback(sender, cq, rbac, tm, state)
        except Exception as exc:
            print(f"⚠️ Menu callback error: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sender.answer_callback(cb_id, f"❌ {exc}")

    elif cb_data.startswith("/"):
        try:
            sender.answer_callback(cb_id, "")
            fake_msg = cq.get("message", {})
            fake_msg["text"] = cb_data
            fake_msg["from"] = cq.get("from", {})
            from menu_handler import handle_command
            handle_command(sender, fake_msg, rbac, tm, state)
        except Exception as exc:
            print(f"⚠️ Callback command error: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    else:
        sender.answer_callback(cb_id, "此功能開發中")

    return 0


if __name__ == "__main__":
    sys.exit(main())
