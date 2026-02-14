#!/usr/bin/env python3
"""
Callback Poller — 即時處理 Telegram inline button 回呼
═══════════════════════════════════════════════════════════
輕量級長輪詢 daemon，專責處理所有 callback_query。

架構分工（allowed_updates 分流）：
  Gateway        → message（AI 對話 + /指令）
  callback_poller → callback_query（選單按鈕，即時回應）
  health_engine  → 不碰 getUpdates（純監控/告警/儀表板更新）

特性：
  · 長輪詢 timeout=25s — 無 callback 時幾乎零 CPU
  · 收到 callback 立即處理 — 回應延遲 <1 秒
  · 自動載入 menu_handler 路由（m: 子選單 + / 指令按鈕）
  · 自動重連（網路錯誤自動退避重試）
  · 共用 health_engine 的 tenant state（同一份 state.json）
"""

import json
import os
import sys
import time
import signal
import requests

# ── 路徑設定 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

ENV_FILE = os.path.join(BASE_DIR, ".env")
STATE_DIR = "/root/.openclaw/monitoring"
PID_FILE = os.path.join(STATE_DIR, "callback_poller.pid")

# ── 常量 ──
POLL_TIMEOUT = 25       # Telegram long-poll 秒數（建議 < 30）
REQUEST_TIMEOUT = 30    # requests timeout（> POLL_TIMEOUT）
MAX_BACKOFF = 60        # 最大退避秒數
INITIAL_BACKOFF = 2     # 初始退避秒數


# ═══════════════════════════════════════════════════════════
# 環境與初始化
# ═══════════════════════════════════════════════════════════

def load_env():
    """從 .env 載入環境變數。"""
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
    """載入主租戶的 state.json。"""
    # 找到第一個租戶目錄
    tenants_dir = os.path.join(STATE_DIR, "tenants")
    if not os.path.isdir(tenants_dir):
        return {}
    for name in os.listdir(tenants_dir):
        state_file = os.path.join(tenants_dir, name, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
    return {}


def save_state_field(field: str, value):
    """更新主租戶 state.json 的單一欄位（原子寫入）。"""
    tenants_dir = os.path.join(STATE_DIR, "tenants")
    if not os.path.isdir(tenants_dir):
        return
    for name in os.listdir(tenants_dir):
        state_file = os.path.join(tenants_dir, name, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                state[field] = value
                tmp = state_file + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                os.replace(tmp, state_file)
            except Exception as e:
                print(f"⚠️ save_state_field({field}) failed: {e}")
            return


# ═══════════════════════════════════════════════════════════
# Telegram API（精簡版，只需要 getUpdates + answerCallback）
# ═══════════════════════════════════════════════════════════

class TelegramPoller:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def get_updates(self, offset: int) -> list:
        """長輪詢 getUpdates — 只請求 callback_query。"""
        r = requests.post(
            f"{self.base}/getUpdates",
            json={
                "offset": offset,
                "timeout": POLL_TIMEOUT,
                "allowed_updates": ["callback_query"],
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("ok"):
            return data.get("result", [])
        return []

    def answer_callback(self, callback_query_id: str, text: str = "") -> bool:
        try:
            r = requests.post(
                f"{self.base}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id, "text": text},
                timeout=5,
            )
            return r.status_code == 200
        except Exception:
            return False

    def send(self, text: str, keyboard: list = None, reply_markup=None, pin: bool = False) -> int:
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
        elif keyboard:
            payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
        try:
            r = requests.post(f"{self.base}/sendMessage", json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            msg_id = int(data["result"]["message_id"])
            if pin:
                self._pin(msg_id)
            return msg_id
        except Exception as exc:
            print(f"⚠️ send failed: {exc}")
            return 0

    def edit(self, message_id: int, text: str, keyboard: list = None) -> bool:
        payload = {
            "chat_id": self.chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if keyboard:
            payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
        try:
            r = requests.post(f"{self.base}/editMessageText", json=payload, timeout=20)
            return r.status_code == 200 and r.json().get("ok", False)
        except Exception:
            return False

    def _pin(self, message_id: int):
        try:
            requests.post(
                f"{self.base}/pinChatMessage",
                json={"chat_id": self.chat_id, "message_id": message_id, "disable_notification": True},
                timeout=10,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# Callback 路由
# ═══════════════════════════════════════════════════════════

def route_callback(poller: TelegramPoller, cq: dict, state: dict):
    """
    路由單一 callback_query。

    規則：
      m:*             → menu_handler.handle_menu_callback()
      /*              → menu_handler.handle_command()（轉為 fake message）
      commands_page_* → toast 提示
      mdl_*           → toast 提示
      其他            → toast 提示
    """
    cb_data = cq.get("data", "")
    cb_id = cq.get("id", "")

    # 延遲 import — 減少啟動時間、確保最新代碼
    from rbac import RBACManager
    from tenant_manager import TenantManager

    rbac = RBACManager()
    tm = TenantManager()

    if cb_data.startswith("m:"):
        try:
            from menu_handler import handle_menu_callback
            handle_menu_callback(poller, cq, rbac, tm, state)
        except Exception as exc:
            print(f"⚠️ Menu callback error: {exc}")
            poller.answer_callback(cb_id, f"❌ {exc}")

    elif cb_data.startswith("/"):
        try:
            poller.answer_callback(cb_id, "")
            fake_msg = cq.get("message", {})
            fake_msg["text"] = cb_data
            fake_msg["from"] = cq.get("from", {})
            from menu_handler import handle_command
            handle_command(poller, fake_msg, rbac, tm, state)
        except Exception as exc:
            print(f"⚠️ Callback command error: {exc}")

    elif cb_data.startswith("commands_page_") or cb_data.startswith("mdl_"):
        poller.answer_callback(cb_id, "請直接輸入 /commands 或 /model")

    else:
        poller.answer_callback(cb_id, "此功能開發中")


# ═══════════════════════════════════════════════════════════
# 主循環
# ═══════════════════════════════════════════════════════════

_running = True

def _handle_signal(signum, frame):
    global _running
    print(f"\n🛑 收到信號 {signum}，正在停止...")
    _running = False


def main():
    global _running

    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未設定")
        return 1

    # 寫入 PID 檔
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    # 信號處理
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    poller = TelegramPoller(token, chat_id)

    # 讀取起始 offset
    state = load_state()
    offset = state.get("last_update_id", 0) + 1
    backoff = 0

    print(f"🚀 Callback Poller 啟動 (PID={os.getpid()}, offset={offset})")
    print(f"   long-poll timeout={POLL_TIMEOUT}s, allowed_updates=[callback_query]")

    while _running:
        try:
            updates = poller.get_updates(offset)
            backoff = 0  # 成功重設退避

            if not updates:
                continue

            for update in updates:
                uid = update.get("update_id", 0)
                if uid >= offset:
                    offset = uid + 1

                cq = update.get("callback_query")
                if not cq:
                    continue

                cb_data = cq.get("data", "")
                from_user = cq.get("from", {}).get("username", "?")
                print(f"📩 callback: {cb_data} (from @{from_user})")

                try:
                    # 每次重新讀取 state 確保與 health_engine 同步
                    state = load_state()
                    route_callback(poller, cq, state)
                except Exception as exc:
                    print(f"❌ route_callback error: {exc}")
                    try:
                        poller.answer_callback(cq.get("id", ""), f"❌ 處理失敗")
                    except Exception:
                        pass

            # 持久化 offset
            save_state_field("last_update_id", offset - 1)

        except requests.exceptions.Timeout:
            # 長輪詢超時 — 正常行為，直接重試
            continue

        except requests.exceptions.ConnectionError as e:
            backoff = min(backoff * 2 or INITIAL_BACKOFF, MAX_BACKOFF)
            print(f"⚠️ 連線錯誤，{backoff}s 後重試: {e}")
            time.sleep(backoff)

        except Exception as e:
            backoff = min(backoff * 2 or INITIAL_BACKOFF, MAX_BACKOFF)
            print(f"❌ 未預期錯誤，{backoff}s 後重試: {e}")
            time.sleep(backoff)

    # 清理
    try:
        os.remove(PID_FILE)
    except Exception:
        pass
    print("🛑 Callback Poller 已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
