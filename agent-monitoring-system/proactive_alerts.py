#!/usr/bin/env python3
"""
⚠️ DEPRECATED — 此腳本已被 health_engine.py 取代。
請勿手動執行，以免 getUpdates API 衝突。

原職責（已整合到 health_engine.py）：
  - 主動警報系統 — 附帶 Inline Buttons 快速操作
  - 當系統資源超標或 Gateway 異常時，發送獨立警報訊息
"""

import sys
print("⚠️ proactive_alerts.py 已被 health_engine.py 取代，請勿手動執行")
print("   使用: python3 health_engine.py")
sys.exit(0)

# ── 以下為舊版程式碼，保留供參考 ──

import json
import os
import subprocess
from datetime import datetime, timezone, timedelta

import requests

TZ_GMT8 = timezone(timedelta(hours=8))
STATE_FILE = "/root/.openclaw/monitoring/proactive_alert_state.json"
ENV_FILE = "/root/.openclaw/workspace/agent-monitoring-system/.env"

# 預設閾值
DEFAULT_THRESHOLDS = {
    "cpu_percent": 80.0,
    "memory_percent": 85.0,
    "disk_percent": 90.0,
    "load_avg_1m": 6.0,
    "gateway_down": True,
}

# 冷卻時間 (秒) — 不同類型警報使用不同的冷卻時間
COOLDOWN_SECONDS = {
    "gateway_down": 120,      # 2 分鐘（關鍵服務，需要快速響應）
    "cpu_percent": 600,       # 10 分鐘
    "memory_percent": 600,    # 10 分鐘
    "disk_percent": 600,      # 10 分鐘
    "load_avg_1m": 600,       # 10 分鐘
}
DEFAULT_COOLDOWN = 600  # 未定義的警報類型使用 10 分鐘


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
        return {
            "last_alerts": {},
            "thresholds": DEFAULT_THRESHOLDS.copy(),
            "last_update_id": 0  # 記錄已處理的 Telegram update
        }
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 確保 thresholds 存在
    if "thresholds" not in data:
        data["thresholds"] = DEFAULT_THRESHOLDS.copy()
    return data


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ─── 系統偵測 ──────────────────────────────────────────────

def sh(cmd: str) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def get_cpu() -> float:
    v = sh("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
    try:
        return float(v)
    except ValueError:
        return 0.0


def get_memory() -> float:
    v = sh("free | grep Mem | awk '{print $3/$2 * 100.0}'")
    try:
        return float(v)
    except ValueError:
        return 0.0


def get_disk() -> float:
    v = sh("df -h / | tail -1 | awk '{print $5}' | sed 's/%//'")
    try:
        return float(v)
    except ValueError:
        return 0.0


def get_load() -> float:
    v = sh("cat /proc/loadavg | awk '{print $1}'")
    try:
        return float(v)
    except ValueError:
        return 0.0


def gateway_is_running() -> bool:
    try:
        # 確保 cron 環境下也能訪問 systemd
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
        
        r = subprocess.run(
            ["systemctl", "--user", "is-active", "openclaw-gateway"],
            capture_output=True, text=True, timeout=10, env=env
        )
        return r.stdout.strip() == "active"
    except Exception:
        return False


# ─── 警報判斷 ──────────────────────────────────────────────

def check_alerts(thresholds: dict) -> list[dict]:
    alerts = []
    now_ts = datetime.now(TZ_GMT8).isoformat()

    cpu = get_cpu()
    if cpu > thresholds.get("cpu_percent", 80):
        alerts.append({
            "type": "cpu_high",
            "severity": "warning" if cpu < 95 else "critical",
            "title": "⚠️ CPU 使用率過高",
            "detail": f"目前 CPU: <b>{cpu:.1f}%</b> (閾值: {thresholds['cpu_percent']}%)",
            "timestamp": now_ts,
        })

    mem = get_memory()
    if mem > thresholds.get("memory_percent", 85):
        alerts.append({
            "type": "memory_high",
            "severity": "warning" if mem < 95 else "critical",
            "title": "⚠️ 記憶體使用率過高",
            "detail": f"目前記憶體: <b>{mem:.1f}%</b> (閾值: {thresholds['memory_percent']}%)",
            "timestamp": now_ts,
        })

    disk = get_disk()
    if disk > thresholds.get("disk_percent", 90):
        alerts.append({
            "type": "disk_high",
            "severity": "warning" if disk < 95 else "critical",
            "title": "🗄️ 磁碟空間不足",
            "detail": f"目前磁碟使用: <b>{disk:.1f}%</b> (閾值: {thresholds['disk_percent']}%)",
            "timestamp": now_ts,
        })

    load = get_load()
    if load > thresholds.get("load_avg_1m", 6.0):
        alerts.append({
            "type": "load_high",
            "severity": "warning",
            "title": "📈 系統負載過高",
            "detail": f"1 分鐘負載: <b>{load:.2f}</b> (閾值: {thresholds['load_avg_1m']})",
            "timestamp": now_ts,
        })

    if thresholds.get("gateway_down", True) and not gateway_is_running():
        alerts.append({
            "type": "gateway_down",
            "severity": "critical",
            "title": "🔴 Gateway 已停止運行！",
            "detail": "OpenClaw Gateway 服務偵測為非 active 狀態",
            "timestamp": now_ts,
        })

    return alerts


# ─── Inline Buttons 構建 ──────────────────────────────────

def build_inline_keyboard(alert_type: str) -> list[list[dict]]:
    """根據警報類型生成 inline keyboard"""
    common_buttons = [
        [
            {"text": "🔄 重啟 Gateway", "callback_data": "/restart"},
            {"text": "📊 查看狀態", "callback_data": "/status"},
        ],
        [
            {"text": "📋 查看日誌", "callback_data": "/logs"},
            {"text": "🖥️ 效能概覽", "callback_data": "/perf"},
        ],
    ]

    if alert_type == "gateway_down":
        return [
            [
                {"text": "🔄 立即重啟 Gateway", "callback_data": "/restart"},
            ],
            [
                {"text": "📋 查看日誌", "callback_data": "/logs"},
                {"text": "🩺 健康檢查", "callback_data": "/health"},
            ],
        ]
    elif alert_type in ("cpu_high", "load_high"):
        return [
            [
                {"text": "📊 查看任務列表", "callback_data": "/tasks"},
                {"text": "🛑 停止任務", "callback_data": "/stop"},
            ],
            [
                {"text": "🔄 重啟 Gateway", "callback_data": "/restart"},
                {"text": "🖥️ 效能概覽", "callback_data": "/perf"},
            ],
        ]
    elif alert_type in ("memory_high",):
        return [
            [
                {"text": "📊 查看任務列表", "callback_data": "/tasks"},
                {"text": "🧹 清理記憶體", "callback_data": "/exec free pagecache"},
            ],
            [
                {"text": "🔄 重啟 Gateway", "callback_data": "/restart"},
                {"text": "🖥️ 效能概覽", "callback_data": "/perf"},
            ],
        ]
    elif alert_type == "disk_high":
        return [
            [
                {"text": "🗑️ 清理日誌", "callback_data": "/exec cleanup logs"},
                {"text": "📋 磁碟詳情", "callback_data": "/exec df -h"},
            ],
            [
                {"text": "🔄 重啟 Gateway", "callback_data": "/restart"},
            ],
        ]

    return common_buttons


# ─── Telegram 傳送 ────────────────────────────────────────

class TelegramAlertSender:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def send_alert(self, text: str, keyboard: list[list[dict]]) -> int:
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if keyboard:
            payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})

        r = requests.post(f"{self.base}/sendMessage", json=payload, timeout=20)
        r.raise_for_status()
        result = r.json()
        if not result.get("ok"):
            raise RuntimeError(f"sendMessage failed: {result}")
        return int(result["result"]["message_id"])
    
    def get_updates(self, offset: int = 0) -> list:
        """獲取 Telegram updates（包含按鈕點擊）"""
        # 使用短超時避免與 Gateway 的 long polling 衝突
        payload = {"offset": offset, "timeout": 0, "allowed_updates": ["callback_query"]}
        try:
            r = requests.post(f"{self.base}/getUpdates", json=payload, timeout=3)
            r.raise_for_status()
            result = r.json()
            if result.get("ok"):
                return result.get("result", [])
        except Exception as e:
            # 如果遇到衝突，靜默忽略（Gateway 正在處理）
            if "409" not in str(e):
                print(f"⚠️ 獲取 updates 失敗: {e}")
        return []
    
    def answer_callback(self, callback_query_id: str, text: str = "") -> bool:
        """回應按鈕點擊"""
        payload = {"callback_query_id": callback_query_id, "text": text}
        try:
            r = requests.post(f"{self.base}/answerCallbackQuery", json=payload, timeout=5)
            return r.status_code == 200
        except Exception:
            return False
    
    def send_message(self, text: str) -> int:
        """發送簡單文字訊息"""
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        try:
            r = requests.post(f"{self.base}/sendMessage", json=payload, timeout=10)
            r.raise_for_status()
            result = r.json()
            if result.get("ok"):
                return int(result["result"]["message_id"])
        except Exception as e:
            print(f"⚠️ 發送訊息失敗: {e}")
        return 0


# ─── 冷卻檢查 ─────────────────────────────────────────────

def is_cooled_down(last_alerts: dict, alert_type: str) -> bool:
    """檢查是否已冷卻（可以發送新警報）"""
    last_ts = last_alerts.get(alert_type)
    if not last_ts:
        return True
    try:
        last_dt = datetime.fromisoformat(last_ts)
        now = datetime.now(TZ_GMT8)
        # 如果 last_dt 沒有 tzinfo，加上
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=TZ_GMT8)
        # 根據警報類型使用不同的冷卻時間
        cooldown = COOLDOWN_SECONDS.get(alert_type, DEFAULT_COOLDOWN)
        return (now - last_dt).total_seconds() >= cooldown
    except Exception:
        return True


# ─── 處理重啟按鈕點擊 ─────────────────────────────────────

def handle_restart_callbacks(sender: 'TelegramAlertSender', last_update_id: int) -> int:
    """
    處理 Telegram 按鈕點擊（即使 Gateway 停止也能執行重啟）
    返回最新的 update_id
    """
    updates = sender.get_updates(offset=last_update_id + 1)
    if not updates:
        return last_update_id
    
    new_update_id = last_update_id
    for update in updates:
        update_id = update.get("update_id", 0)
        if update_id > new_update_id:
            new_update_id = update_id
        
        callback_query = update.get("callback_query")
        if not callback_query:
            continue
        
        callback_id = callback_query.get("id")
        callback_data = callback_query.get("data", "")
        from_user = callback_query.get("from", {}).get("username", "unknown")
        
        # 處理 /restart 命令
        if callback_data == "/restart":
            print(f"🔄 收到來自 @{from_user} 的重啟請求")
            sender.answer_callback(callback_id, "正在重啟 Gateway...")
            
            try:
                # 執行重啟 - 使用完整的環境變數
                env = os.environ.copy()
                env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
                env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
                
                result = subprocess.run(
                    ["systemctl", "--user", "restart", "openclaw-gateway"],
                    capture_output=True, text=True, timeout=10, env=env
                )
                if result.returncode == 0:
                    print(f"✅ Gateway 重啟命令已執行")
                    sender.send_message("🔄 <b>Gateway 重啟中</b>\n請稍候約 1 分鐘，系統會自動發送重啟完成通知")
                else:
                    print(f"❌ Gateway 重啟失敗: {result.stderr}")
                    sender.send_message(f"❌ Gateway 重啟失敗\n{result.stderr}")
            except Exception as e:
                print(f"❌ 執行重啟時發生錯誤: {e}")
                sender.send_message(f"❌ 執行重啟時發生錯誤: {e}")
        else:
            # 其他按鈕由 Gateway 處理，這裡只回應
            sender.answer_callback(callback_id, "此功能需要 Gateway 運行")
    
    return new_update_id


# ─── 主程式 ───────────────────────────────────────────────

def main() -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未設定")
        return 1

    state = load_state()
    thresholds = state.get("thresholds", DEFAULT_THRESHOLDS.copy())
    last_alerts = state.get("last_alerts", {})
    last_status = state.get("last_status", {})  # 記錄上次各項目的狀態
    last_update_id = state.get("last_update_id", 0)  # 記錄已處理的 update
    
    sender = TelegramAlertSender(token, chat_id)
    
    # 1. 只在 Gateway 停止時才處理重啟按鈕（避免與運行中的 Gateway 衝突）
    current_gateway_running = gateway_is_running()
    if not current_gateway_running:
        new_update_id = handle_restart_callbacks(sender, last_update_id)
        if new_update_id > last_update_id:
            state["last_update_id"] = new_update_id
            save_state(state)
    else:
        # Gateway 運行中，由它自己處理所有按鈕點擊
        pass

    # 2. 檢查並發送警報
    alerts = check_alerts(thresholds)
    
    # 檢查 Gateway 當前狀態
    last_gateway_running = last_status.get("gateway_running", True)
    
    # 過濾掉不需要發送的警報
    filtered_alerts = []
    for alert in alerts:
        a_type = alert["type"]
        
        # 特殊處理 gateway_down：只在狀態從 running → down 時警報
        if a_type == "gateway_down":
            if last_gateway_running:  # 上次是運行中，現在 down 了 → 狀態轉換
                filtered_alerts.append(alert)
            else:
                print(f"⏸️ Gateway 仍處於停止狀態，跳過重複警報")
        else:
            # 其他警報使用冷卻機制
            if is_cooled_down(last_alerts, a_type):
                filtered_alerts.append(alert)
            else:
                print(f"⏸️ {a_type} 仍在冷卻中，跳過")
    
    alerts = filtered_alerts
    
    if not alerts:
        print("✅ 系統正常，無需發送警報")
        # 更新 Gateway 狀態（即使沒有警報也要記錄）
        state["last_status"] = {"gateway_running": current_gateway_running}
        save_state(state)
        return 0

    # sender 已在上面創建了
    sent_count = 0

    for alert in alerts:
        a_type = alert["type"]
        # 警報已經在上面過濾過了，這裡直接發送

        severity_icon = "🚨" if alert["severity"] == "critical" else "⚠️"
        text = (
            f"{severity_icon} <b>系統警報</b>\n"
            f"{'━' * 25}\n"
            f"{alert['title']}\n\n"
            f"{alert['detail']}\n\n"
            f"<code>時間: {datetime.now(TZ_GMT8).strftime('%Y-%m-%d %H:%M:%S')} GMT+8</code>\n"
            f"<code>嚴重度: {alert['severity'].upper()}</code>"
        )

        keyboard = build_inline_keyboard(a_type)

        try:
            msg_id = sender.send_alert(text, keyboard)
            last_alerts[a_type] = datetime.now(TZ_GMT8).isoformat()
            sent_count += 1
            print(f"🔔 已發送 {a_type} 警報 (msg_id={msg_id})")
        except Exception as e:
            print(f"❌ 發送 {a_type} 警報失敗: {e}")

    # 保存狀態（包含最後的 Gateway 狀態）
    state["last_alerts"] = last_alerts
    state["last_status"] = {"gateway_running": current_gateway_running}
    save_state(state)
    print(f"✅ 共發送 {sent_count} 則警報")
    return 0


if __name__ == "__main__":
    sys.exit(main())
