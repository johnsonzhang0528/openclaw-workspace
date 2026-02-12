#!/usr/bin/env python3
"""
Gateway 重啟完成監測器
監測 Gateway 重啟狀態並在完成後發送 Telegram 通知
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

TZ_GMT8 = timezone(timedelta(hours=8))
ENV_FILE = "/root/.openclaw/workspace/agent-monitoring-system/.env"


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


def gateway_is_running() -> bool:
    """檢查 Gateway 是否正在運行"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "openclaw-gateway"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def get_uptime_seconds() -> int:
    """取得 Gateway 運行時間（秒）"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", "openclaw-gateway", "--property=ActiveEnterTimestamp"],
            capture_output=True, text=True, timeout=10,
        )
        # 輸出格式: ActiveEnterTimestamp=Thu 2026-02-12 21:38:41 CST
        line = result.stdout.strip()
        if not line or "=" not in line:
            return 0
        timestamp_str = line.split("=", 1)[1].strip()
        if not timestamp_str or timestamp_str == "n/a":
            return 0
        
        # 解析時間並計算運行時間
        from datetime import datetime
        try:
            # 移除時區縮寫
            timestamp_str = " ".join(timestamp_str.split()[:-1])
            active_time = datetime.strptime(timestamp_str, "%a %Y-%m-%d %H:%M:%S")
            now = datetime.now()
            uptime = (now - active_time).total_seconds()
            return int(uptime)
        except Exception:
            return 0
    except Exception:
        return 0


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
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未設定")
        return 1

    sender = TelegramSender(token, chat_id)
    
    # 等待 Gateway 完全停止（最多等待 5 秒）
    print("⏳ 等待 Gateway 停止...")
    for i in range(10):
        if not gateway_is_running():
            print("✓ Gateway 已停止")
            break
        time.sleep(0.5)
    else:
        print("⚠ Gateway 似乎沒有停止")
    
    # 等待 Gateway 重新啟動（最多等待 15 秒）
    print("⏳ 等待 Gateway 重新啟動...")
    for i in range(30):
        if gateway_is_running():
            uptime = get_uptime_seconds()
            if uptime < 20:  # 如果運行時間少於 20 秒，表示是剛重啟的
                print(f"✓ Gateway 已重新啟動 (運行時間: {uptime}秒)")
                time.sleep(2)  # 再等 2 秒確保完全啟動
                
                # 發送成功通知
                now = datetime.now(TZ_GMT8)
                text = (
                    f"✅ <b>Gateway 重啟完成</b>\n"
                    f"{'━' * 25}\n"
                    f"狀態: 🟢 運行中\n"
                    f"完成時間: {now.strftime('%Y-%m-%d %H:%M:%S')} GMT+8\n"
                    f"啟動耗時: 約 {uptime} 秒"
                )
                try:
                    sender.send(text)
                    print("✅ 已發送 Telegram 通知")
                except Exception as e:
                    print(f"❌ 發送通知失敗: {e}")
                
                return 0
        time.sleep(0.5)
    
    # 超時 - Gateway 未能在時間內啟動
    print("❌ Gateway 重啟超時")
    text = (
        f"❌ <b>Gateway 重啟失敗</b>\n"
        f"{'━' * 25}\n"
        f"Gateway 在 15 秒內未能成功啟動\n"
        f"請手動檢查服務狀態:\n"
        f"<code>systemctl --user status openclaw-gateway</code>"
    )
    try:
        sender.send(text)
    except Exception as e:
        print(f"❌ 發送通知失敗: {e}")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
