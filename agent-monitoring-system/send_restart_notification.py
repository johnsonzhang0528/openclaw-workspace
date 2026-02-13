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

    def send(self, text: str) -> int:
        r = requests.post(f"{self.base}/sendMessage", json={
            "chat_id": self.chat_id, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }, timeout=20)
        r.raise_for_status()
        return int(r.json()["result"]["message_id"])


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
    
    # ── 多租戶：通知所有啟用的租戶 ──
    chat_ids = []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tenant_manager import TenantManager
        tm = TenantManager()
        for tenant in tm.get_active_tenants():
            if tenant.get_setting("alerts_enabled", True):
                chat_ids.append(tenant.chat_id)
    except Exception:
        pass

    # 回退：無租戶時用 .env
    if not chat_ids:
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if chat_id:
            chat_ids.append(chat_id)
        else:
            print("❌ 無可通知的租戶")
            return 1

    now_gmt8 = datetime.now(TZ_GMT8)
    text = (
        f"✅ <b>Gateway 重啟完成</b>\n"
        f"{'━' * 25}\n"
        f"狀態: 🟢 運行中\n"
        f"完成時間: {now_gmt8.strftime('%Y-%m-%d %H:%M:%S')} GMT+8\n"
        f"啟動耗時: 約 {uptime:.1f} 秒"
    )

    sent_count = 0
    for cid in chat_ids:
        try:
            sender = TelegramSender(token, cid)
            msg_id = sender.send(text)
            print(f"✅ 已發送重啟通知至 {cid} (msg_id={msg_id})")
            sent_count += 1
        except Exception as e:
            print(f"⚠️ 發送至 {cid} 失敗: {e}")

    if sent_count > 0:
        state["last_restart_time"] = start_time_str
        save_state(state)

    return 0 if sent_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
