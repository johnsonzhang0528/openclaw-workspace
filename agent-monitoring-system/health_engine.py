#!/usr/bin/env python3
"""
統一健康檢查引擎 (Health Engine)
─────────────────────────────────
職責：
  1. 平行採集所有系統指標 → 寫入統一 monitoring_state.json
  2. 計算 0-100 健康分數
  3. 錯誤追蹤：去重、聚合、分級
  4. 自癒：可恢復故障自動修復，連續失敗升級告警
  5. 為 /monitor 提供可直接渲染的快照

取代原本 unified_dashboard_cron.py 與 proactive_alerts.py 的職責，
以單一程序統一執行。
"""

import json
import os
import subprocess
import sys
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

# ─── 多租戶整合 ─────────────────────────────────────────────
# 延遲匯入以避免循環依賴，在 main() 中實際載入
_tenant_manager = None
_rbac_manager = None

def _get_tenant_manager():
    global _tenant_manager
    if _tenant_manager is None:
        from tenant_manager import TenantManager
        _tenant_manager = TenantManager()
    return _tenant_manager

def _get_rbac_manager():
    global _rbac_manager
    if _rbac_manager is None:
        from rbac import RBACManager
        _rbac_manager = RBACManager()
    return _rbac_manager

# ─── 常數 ──────────────────────────────────────────────────

TZ_GMT8 = timezone(timedelta(hours=8))
BASE_DIR = "/root/.openclaw/monitoring"
STATE_FILE = os.path.join(BASE_DIR, "monitoring_state.json")
ERROR_LOG = os.path.join(BASE_DIR, "error_events.jsonl")
ENV_FILE = "/root/.openclaw/workspace/agent-monitoring-system/.env"

# 健康分數權重
WEIGHT_GATEWAY = 30
WEIGHT_CPU = 15
WEIGHT_MEM = 15
WEIGHT_DISK = 10
WEIGHT_LOAD = 10
WEIGHT_CRON = 10
WEIGHT_ERROR_RATE = 10

# 自癒
MAX_AUTO_RESTART_ATTEMPTS = 3
AUTO_RESTART_COOLDOWN_SEC = 300  # 連續自動重啟之間至少 5 分鐘

# 警報冷卻
ALERT_COOLDOWN = {
    "gateway_down": 120,
    "cpu_high": 600,
    "memory_high": 600,
    "disk_high": 600,
    "load_high": 600,
    "cron_missing": 600,
    "error_spike": 600,
}

# 閾值
THRESHOLDS = {
    "cpu_percent": 80.0,
    "memory_percent": 85.0,
    "disk_percent": 90.0,
    "load_avg_1m": 6.0,
}


# ─── 工具函式 ──────────────────────────────────────────────

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


def sh(cmd: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def now_ts() -> str:
    return datetime.now(TZ_GMT8).strftime("%Y-%m-%d %H:%M:%S")


def now_iso() -> str:
    return datetime.now(TZ_GMT8).isoformat()


def ensure_dir():
    os.makedirs(BASE_DIR, exist_ok=True)


# ─── 狀態持久化 ───────────────────────────────────────────

def load_state() -> dict:
    ensure_dir()
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _default_state()


def save_state(state: dict) -> None:
    ensure_dir()
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def _default_state() -> dict:
    return {
        "version": 2,
        "last_updated": now_iso(),
        "health_score": 100,
        "health_grade": "A",
        # 最新快照（供 /monitor 直接使用）
        "snapshot": {
            "gateway_active": True,
            "gateway_uptime_sec": 0,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_used_mb": 0,
            "memory_total_mb": 0,
            "disk_percent": 0.0,
            "disk_used_gb": 0.0,
            "disk_total_gb": 0.0,
            "load_1m": 0.0,
            "load_5m": 0.0,
            "load_15m": 0.0,
            "subagent_total": 0,
            "subagent_active": 0,
            "sessions_today": 0,
            "sessions_completed": 0,
            "sessions_failed": 0,
            "cron_jobs_ok": 0,
            "cron_jobs_total": 0,
        },
        # 警報狀態
        "alerts": {
            "last_sent": {},     # type → iso timestamp
            "active_alerts": [], # 當前未恢復的告警
        },
        # 自癒狀態
        "self_heal": {
            "gateway_restart_count": 0,
            "last_restart_attempt": None,
        },
        # 錯誤追蹤
        "errors": {
            "recent": [],          # 最近 50 筆摘要
            "today_count": 0,
            "today_date": datetime.now(TZ_GMT8).strftime("%Y-%m-%d"),
        },
        # Gateway 狀態追蹤
        "gateway_prev_running": True,
        # dashboard 訊息 id（繼承舊 unified_dashboard）
        "dashboard_message_id": None,
        # Telegram update id（繼承舊 proactive_alerts）
        "last_update_id": 0,
    }


# ─── 平行採集 ────────────────────────────────────────────

def collect_cpu() -> Dict[str, float]:
    """
    讀取 /proc/stat 計算 CPU 使用率（3 次取樣取平均，間隔 0.5 秒）。
    比 top -bn1 穩定，不受瞬時 spike 影響。
    """
    samples = []
    prev = None
    for _ in range(4):  # 4 個時間點 → 3 個區間
        with open("/proc/stat") as f:
            fields = f.readline().split()  # cpu user nice system idle iowait irq softirq ...
        vals = [int(x) for x in fields[1:]]
        total = sum(vals)
        idle = vals[3] + vals[4]  # idle + iowait
        if prev is not None:
            dt = total - prev[0]
            di = idle - prev[1]
            if dt > 0:
                samples.append((1.0 - di / dt) * 100.0)
        prev = (total, idle)
        if _ < 3:
            time.sleep(0.5)
    if samples:
        return {"cpu_percent": round(sum(samples) / len(samples), 1)}
    return {"cpu_percent": 0.0}


def collect_memory() -> Dict[str, Any]:
    pct = sh("free | grep Mem | awk '{print $3/$2 * 100.0}'")
    used = sh("free -m | grep Mem | awk '{print $3}'")
    total = sh("free -m | grep Mem | awk '{print $2}'")
    try:
        return {
            "memory_percent": float(pct),
            "memory_used_mb": int(used),
            "memory_total_mb": int(total),
        }
    except (ValueError, TypeError):
        return {"memory_percent": 0.0, "memory_used_mb": 0, "memory_total_mb": 0}


def collect_disk() -> Dict[str, Any]:
    pct = sh("df -h / | tail -1 | awk '{print $5}' | sed 's/%//'")
    used = sh("df -BG / | tail -1 | awk '{print $3}' | sed 's/G//'")
    total = sh("df -BG / | tail -1 | awk '{print $2}' | sed 's/G//'")
    try:
        return {
            "disk_percent": float(pct),
            "disk_used_gb": float(used),
            "disk_total_gb": float(total),
        }
    except (ValueError, TypeError):
        return {"disk_percent": 0.0, "disk_used_gb": 0.0, "disk_total_gb": 0.0}


def collect_load() -> Dict[str, float]:
    raw = sh("cat /proc/loadavg")
    parts = raw.split()
    try:
        return {
            "load_1m": float(parts[0]),
            "load_5m": float(parts[1]),
            "load_15m": float(parts[2]),
        }
    except (IndexError, ValueError):
        return {"load_1m": 0.0, "load_5m": 0.0, "load_15m": 0.0}


def collect_gateway() -> Dict[str, Any]:
    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", "openclaw-gateway"],
            capture_output=True, text=True, timeout=5, env=env,
        )
        active = r.stdout.strip() == "active"
    except Exception:
        active = False

    uptime_sec = 0
    if active:
        raw = sh("systemctl --user show openclaw-gateway --property=ActiveEnterTimestamp 2>/dev/null")
        # ActiveEnterTimestamp=Thu 2026-02-13 04:00:00 CST
        if "=" in raw:
            ts_str = raw.split("=", 1)[1].strip()
            if ts_str:
                try:
                    from dateutil.parser import parse as dateparse
                    dt = dateparse(ts_str)
                    uptime_sec = max(0, int((datetime.now(dt.tzinfo or TZ_GMT8) - dt).total_seconds()))
                except Exception:
                    pass

    return {"gateway_active": active, "gateway_uptime_sec": uptime_sec}


def collect_subagents() -> Dict[str, Any]:
    try:
        r = subprocess.run(
            ["openclaw", "sessions", "list", "--json", "--kinds", "subagent"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return {"subagent_total": 0, "subagent_active": 0}
        data = json.loads(r.stdout)
        sessions = data.get("sessions", [])
        active_cutoff_ms = 5 * 60 * 1000
        active_count = sum(1 for s in sessions if int(s.get("ageMs", 10**9)) <= active_cutoff_ms)
        return {"subagent_total": len(sessions), "subagent_active": active_count}
    except Exception:
        return {"subagent_total": 0, "subagent_active": 0}


def collect_cron() -> Dict[str, Any]:
    """檢查 cron 排程是否正常"""
    expected_scripts = [
        "run_health_engine.sh",
        "run_dev_daily_report.sh",
        "run_usage_report.sh",
        "check_recent_restart.sh",
    ]
    try:
        crontab = sh("crontab -l 2>/dev/null")
        ok = sum(1 for s in expected_scripts if s in crontab)
        return {"cron_jobs_ok": ok, "cron_jobs_total": len(expected_scripts)}
    except Exception:
        return {"cron_jobs_ok": 0, "cron_jobs_total": len(expected_scripts)}


def collect_all_parallel() -> dict:
    """平行採集所有系統指標"""
    results: dict = {}
    collectors = [
        collect_cpu,
        collect_memory,
        collect_disk,
        collect_load,
        collect_gateway,
        collect_subagents,
        collect_cron,
    ]
    with ThreadPoolExecutor(max_workers=len(collectors)) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in collectors}
        for future in as_completed(futures):
            try:
                data = future.result(timeout=20)
                results.update(data)
            except Exception as exc:
                print(f"⚠️ 採集 {futures[future]} 失敗: {exc}")
    return results


# ─── 健康分數計算 ─────────────────────────────────────────

def compute_health_score(snap: dict) -> Tuple[int, str]:
    """
    0-100 分，越高越健康。
    各項依權重扣分。
    """
    score = 100

    # Gateway
    if not snap.get("gateway_active"):
        score -= WEIGHT_GATEWAY
    
    # CPU
    cpu = snap.get("cpu_percent", 0)
    if cpu > 95:
        score -= WEIGHT_CPU
    elif cpu > THRESHOLDS["cpu_percent"]:
        score -= int(WEIGHT_CPU * (cpu - THRESHOLDS["cpu_percent"]) / (100 - THRESHOLDS["cpu_percent"]))

    # Memory
    mem = snap.get("memory_percent", 0)
    if mem > 95:
        score -= WEIGHT_MEM
    elif mem > THRESHOLDS["memory_percent"]:
        score -= int(WEIGHT_MEM * (mem - THRESHOLDS["memory_percent"]) / (100 - THRESHOLDS["memory_percent"]))

    # Disk
    disk = snap.get("disk_percent", 0)
    if disk > 95:
        score -= WEIGHT_DISK
    elif disk > THRESHOLDS["disk_percent"]:
        score -= int(WEIGHT_DISK * (disk - THRESHOLDS["disk_percent"]) / (100 - THRESHOLDS["disk_percent"]))

    # Load
    load_1m = snap.get("load_1m", 0)
    if load_1m > THRESHOLDS["load_avg_1m"] * 2:
        score -= WEIGHT_LOAD
    elif load_1m > THRESHOLDS["load_avg_1m"]:
        score -= int(WEIGHT_LOAD * 0.5)

    # Cron
    cron_ok = snap.get("cron_jobs_ok", 0)
    cron_total = snap.get("cron_jobs_total", 1)
    if cron_total > 0:
        cron_ratio = cron_ok / cron_total
        score -= int(WEIGHT_CRON * (1 - cron_ratio))

    score = max(0, min(100, score))

    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return score, grade


# ─── 告警判斷 ─────────────────────────────────────────────

@dataclass
class AlertEvent:
    alert_type: str
    severity: str   # critical / warning / info
    title: str
    detail: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = now_iso()


def evaluate_alerts(snap: dict, state: dict, thresholds: dict = None) -> List[AlertEvent]:
    """評估告警。thresholds 可傳入租戶自訂閾值，預設使用全域閾值。"""
    t = thresholds or THRESHOLDS
    events: List[AlertEvent] = []

    # Gateway down（僅在狀態轉換時）
    gw_now = snap.get("gateway_active", True)
    gw_prev = state.get("gateway_prev_running", True)
    if not gw_now and gw_prev:
        events.append(AlertEvent(
            alert_type="gateway_down",
            severity="critical",
            title="🔴 Gateway 已停止運行！",
            detail="OpenClaw Gateway 服務偵測為非 active 狀態",
        ))

    # CPU
    cpu = snap.get("cpu_percent", 0)
    cpu_threshold = t.get("cpu_percent", 80)
    if cpu > cpu_threshold:
        events.append(AlertEvent(
            alert_type="cpu_high",
            severity="critical" if cpu > 95 else "warning",
            title="⚠️ CPU 使用率過高",
            detail=f"目前 CPU: <b>{cpu:.1f}%</b> (閾值: {cpu_threshold}%)",
        ))

    # Memory
    mem = snap.get("memory_percent", 0)
    mem_threshold = t.get("memory_percent", 85)
    if mem > mem_threshold:
        events.append(AlertEvent(
            alert_type="memory_high",
            severity="critical" if mem > 95 else "warning",
            title="⚠️ 記憶體使用率過高",
            detail=f"目前記憶體: <b>{mem:.1f}%</b> (閾值: {mem_threshold}%)",
        ))

    # Disk
    disk = snap.get("disk_percent", 0)
    disk_threshold = t.get("disk_percent", 90)
    if disk > disk_threshold:
        events.append(AlertEvent(
            alert_type="disk_high",
            severity="critical" if disk > 95 else "warning",
            title="🗄️ 磁碟空間不足",
            detail=f"目前磁碟使用: <b>{disk:.1f}%</b> (閾值: {disk_threshold}%)",
        ))

    # Load
    load_val = snap.get("load_1m", 0)
    load_threshold = t.get("load_avg_1m", 6.0)
    if load_val > load_threshold:
        events.append(AlertEvent(
            alert_type="load_high",
            severity="warning",
            title="📈 系統負載過高",
            detail=f"1 分鐘負載: <b>{load_val:.2f}</b> (閾值: {load_threshold})",
        ))

    # Cron 缺失
    cron_ok = snap.get("cron_jobs_ok", 0)
    cron_total = snap.get("cron_jobs_total", 0)
    if cron_total > 0 and cron_ok < cron_total:
        events.append(AlertEvent(
            alert_type="cron_missing",
            severity="warning",
            title="⚠️ Cron 排程不完整",
            detail=f"正常: {cron_ok}/{cron_total} 個排程",
        ))

    return events


def filter_cooled_alerts(events: List[AlertEvent], last_sent: dict) -> List[AlertEvent]:
    now = datetime.now(TZ_GMT8)
    filtered = []
    for evt in events:
        cooldown = ALERT_COOLDOWN.get(evt.alert_type, 600)
        last_ts_str = last_sent.get(evt.alert_type)
        if last_ts_str:
            try:
                last_dt = datetime.fromisoformat(last_ts_str)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=TZ_GMT8)
                if (now - last_dt).total_seconds() < cooldown:
                    continue
            except Exception:
                pass
        filtered.append(evt)
    return filtered


# ─── 自癒 ────────────────────────────────────────────────

def try_self_heal_gateway(state: dict) -> Optional[str]:
    """嘗試自動重啟 Gateway，返回操作描述或 None"""
    heal = state.setdefault("self_heal", {})
    count = heal.get("gateway_restart_count", 0)
    last_attempt = heal.get("last_restart_attempt")

    # 超過最大次數 → 不再自動重啟
    if count >= MAX_AUTO_RESTART_ATTEMPTS:
        return None

    # 冷卻檢查
    if last_attempt:
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=TZ_GMT8)
            if (datetime.now(TZ_GMT8) - last_dt).total_seconds() < AUTO_RESTART_COOLDOWN_SEC:
                return None
        except Exception:
            pass

    # 執行重啟
    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
    try:
        r = subprocess.run(
            ["systemctl", "--user", "restart", "openclaw-gateway"],
            capture_output=True, text=True, timeout=15, env=env,
        )
        heal["gateway_restart_count"] = count + 1
        heal["last_restart_attempt"] = now_iso()
        if r.returncode == 0:
            return f"自動重啟 Gateway（第 {count + 1} 次）"
        else:
            return f"自動重啟失敗: {r.stderr.strip()}"
    except Exception as exc:
        heal["last_restart_attempt"] = now_iso()
        return f"自動重啟異常: {exc}"


def reset_self_heal_on_recovery(state: dict):
    """Gateway 恢復後重設自癒計數器"""
    heal = state.setdefault("self_heal", {})
    heal["gateway_restart_count"] = 0


# ─── 錯誤追蹤 ────────────────────────────────────────────

def record_error(state: dict, error_type: str, component: str, message: str, severity: str = "error"):
    """記錄一筆錯誤事件"""
    errors = state.setdefault("errors", {"recent": [], "today_count": 0, "today_date": ""})
    today = datetime.now(TZ_GMT8).strftime("%Y-%m-%d")
    if errors.get("today_date") != today:
        errors["today_count"] = 0
        errors["today_date"] = today

    errors["today_count"] = errors.get("today_count", 0) + 1

    entry = {
        "ts": now_iso(),
        "type": error_type,
        "component": component,
        "message": message[:200],
        "severity": severity,
    }
    errors.setdefault("recent", []).append(entry)
    # 只保留最近 50 筆
    errors["recent"] = errors["recent"][-50:]

    # 同時 append 到 JSONL 檔案
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ─── Telegram 傳送 ────────────────────────────────────────

class TelegramSender:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def send(self, text: str, keyboard: list = None, pin: bool = False) -> int:
        payload: dict = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if keyboard:
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
            print(f"⚠️ Telegram send failed: {exc}")
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

    def set_my_commands(self, commands: list) -> bool:
        """註冊 Bot 指令選單（Telegram 會在輸入框顯示指令提示）"""
        try:
            r = requests.post(
                f"{self.base}/setMyCommands",
                json={"commands": commands},
                timeout=10,
            )
            return r.status_code == 200 and r.json().get("ok", False)
        except Exception:
            return False

    def get_updates(self, offset: int = 0) -> list:
        try:
            r = requests.post(
                f"{self.base}/getUpdates",
                json={"offset": offset, "timeout": 0, "allowed_updates": ["callback_query", "message"]},
                timeout=3,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("ok"):
                return data.get("result", [])
        except Exception:
            pass
        return []


# ─── 告警按鈕 ────────────────────────────────────────────

def build_keyboard(alert_type: str) -> list:
    if alert_type == "gateway_down":
        return [
            [{"text": "🔄 立即重啟 Gateway", "callback_data": "/restart"}],
            [
                {"text": "📋 查看日誌", "callback_data": "/logs"},
                {"text": "🩺 健康檢查", "callback_data": "/health"},
            ],
        ]
    elif alert_type in ("cpu_high", "load_high"):
        return [
            [
                {"text": "📊 查看任務列表", "callback_data": "/tasks"},
                {"text": "🖥️ 效能概覽", "callback_data": "/perf"},
            ],
        ]
    elif alert_type == "memory_high":
        return [
            [
                {"text": "📊 查看任務列表", "callback_data": "/tasks"},
                {"text": "🖥️ 效能概覽", "callback_data": "/perf"},
            ],
        ]
    elif alert_type == "disk_high":
        return [
            [
                {"text": "📋 磁碟詳情", "callback_data": "/exec df -h"},
                {"text": "🖥️ 效能概覽", "callback_data": "/perf"},
            ],
        ]
    return []


# ─── 儀表板渲染 ──────────────────────────────────────────

def _bar(value: float, width: int = 15) -> str:
    filled = int(value / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _grade_emoji(grade: str) -> str:
    return {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "💀"}.get(grade, "❓")


def render_dashboard(state: dict) -> str:
    snap = state.get("snapshot", {})
    score = state.get("health_score", 0)
    grade = state.get("health_grade", "?")
    ts = state.get("last_updated", "?")

    gw_icon = "🟢" if snap.get("gateway_active") else "🔴"
    gw_uptime = snap.get("gateway_uptime_sec", 0)
    gw_uptime_str = _fmt_uptime(gw_uptime)

    cpu = snap.get("cpu_percent", 0)
    mem = snap.get("memory_percent", 0)
    disk = snap.get("disk_percent", 0)
    load_1 = snap.get("load_1m", 0)
    load_5 = snap.get("load_5m", 0)
    load_15 = snap.get("load_15m", 0)

    mem_used = snap.get("memory_used_mb", 0)
    mem_total = snap.get("memory_total_mb", 0)
    disk_used = snap.get("disk_used_gb", 0)
    disk_total = snap.get("disk_total_gb", 0)

    sub_total = snap.get("subagent_total", 0)
    sub_active = snap.get("subagent_active", 0)
    sess_today = snap.get("sessions_today", 0)
    sess_done = snap.get("sessions_completed", 0)
    sess_fail = snap.get("sessions_failed", 0)

    cron_ok = snap.get("cron_jobs_ok", 0)
    cron_total = snap.get("cron_jobs_total", 0)

    errors_today = state.get("errors", {}).get("today_count", 0)

    lines = [
        f"<b>📌 系統監控儀表板</b>",
        f"{'━' * 30}",
        f"{_grade_emoji(grade)} <b>健康分數: {score}/100 ({grade})</b>",
        f"<code>更新: {ts}</code>",
        "",
        f"<b>🖥️ Gateway</b>",
        f"  {gw_icon} 狀態: {'運行中' if snap.get('gateway_active') else '已停止'}",
        f"  ⏱️ 運行時間: {gw_uptime_str}",
        "",
        f"<b>📊 系統資源</b>",
        f"  CPU  {_severity_icon(cpu)} <code>{_bar(cpu)}</code> {cpu:.1f}%",
        f"  RAM  {_severity_icon(mem)} <code>{_bar(mem)}</code> {mem:.1f}% ({mem_used}/{mem_total}MB)",
        f"  DISK {_severity_icon(disk)} <code>{_bar(disk)}</code> {disk:.1f}% ({disk_used:.1f}/{disk_total:.1f}GB)",
        f"  LOAD: {load_1:.2f} / {load_5:.2f} / {load_15:.2f}",
        "",
        f"<b>🤖 子代理</b>",
        f"  總數: {sub_total} | 活躍: {sub_active}",
        f"  今日會話: {sess_today} (完成 {sess_done} / 失敗 {sess_fail})",
        "",
        f"<b>⚙️ 排程任務</b>",
        f"  Cron: {cron_ok}/{cron_total} 正常",
        "",
        f"<b>🐛 錯誤</b>",
        f"  今日: {errors_today} 筆",
    ]

    # 活躍告警
    active_alerts = state.get("alerts", {}).get("active_alerts", [])
    if active_alerts:
        lines.append("")
        lines.append(f"<b>🚨 活躍告警 ({len(active_alerts)})</b>")
        for a in active_alerts[-5:]:  # 最多顯示 5 則
            lines.append(f"  • {a.get('title', '?')}")

    # 備份狀態（快取 5 分鐘，避免每 30 秒重建 BackupEngine 的 I/O）
    try:
        bk_state_file = os.path.join(BASE_DIR, "..", "backups", "backup_state.json")
        if os.path.exists(bk_state_file):
            with open(bk_state_file, "r") as _bf:
                _bs = json.load(_bf)
            last_bk = _bs.get("last_backup")
            if last_bk:
                bk_ts = last_bk[:16]
                fail = _bs.get("consecutive_failures", 0)
                bk_icon = "🟢" if fail == 0 else "🟡" if fail < 3 else "🔴"
                # 計算可用備份數
                bk_dir = os.path.dirname(bk_state_file)
                bk_count = len([f for f in os.listdir(bk_dir)
                               if f.startswith("backup_") and f.endswith(".tar.gz")])
                lines.append("")
                lines.append(f"<b>💾 備份</b>")
                lines.append(f"  {bk_icon} 最後: {bk_ts} ({bk_count} 份可用)")
                if fail > 0:
                    lines.append(f"  ⚠️ 連續失敗: {fail} 次")
    except Exception:
        pass

    # Token 成本摘要
    try:
        from token_tracker import TokenTracker
        _tt = TokenTracker()
        _tt._load_buckets()
        _ts = _tt.get_today_summary()
        _budget = _tt.get_budget()
        if _ts.get("calls", 0) > 0 or _budget.get("today_cost_usd", 0) > 0:
            _cost_icon = "🟢" if _budget.get("today_pct", 0) < 70 else "🟡" if _budget.get("today_pct", 0) < 90 else "🔴"
            lines.append("")
            lines.append(f"<b>💰 Token 成本</b>")
            lines.append(f"  {_cost_icon} 今日: ${_ts['cost_usd']:.4f} ({_ts['calls']} 次呼叫)")
            lines.append(f"  💳 預算: {_budget['today_pct']:.0f}% (${_budget['daily_limit_usd']:.2f})")
    except Exception as _e:
        print(f"⚠️ Dashboard Token section failed: {_e}")

    return "\n".join(lines)


def _severity_icon(value: float) -> str:
    if value >= 90:
        return "🔴"
    elif value >= 70:
        return "🟡"
    return "🟢"


def _fmt_uptime(sec: int) -> str:
    if sec <= 0:
        return "N/A"
    days, rem = divmod(sec, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}時")
    parts.append(f"{mins}分{secs}秒")
    return "".join(parts)


# ─── Telegram 選單整合 ──────────────────────────────────

def _ensure_bot_commands(sender: TelegramSender, state: dict):
    """
    一次性註冊 Bot 指令選單。
    透過版本號追蹤，只在首次啟動或版本變更時呼叫 setMyCommands。
    """
    from telegram_ui import BOT_COMMANDS
    cmd_version = "v1"  # 變更 BOT_COMMANDS 時遞增
    if state.get("bot_commands_version") == cmd_version:
        return
    if sender.set_my_commands(BOT_COMMANDS):
        state["bot_commands_version"] = cmd_version
        print(f"✅ Bot 指令選單已註冊 ({cmd_version})")


def _process_updates(sender: TelegramSender, state: dict, gw_running: bool, tm, rbac):
    """
    處理所有待處理的 Telegram 更新。

    路由規則：
      - callback_data 以 "m:" 開頭 → 主控面板選單（menu_handler）
      - callback_data == "/restart"  → 舊版告警按鈕（向後相容）
      - callback_data 其他 /指令     → 舊版告警按鈕資訊回應
      - message 以 "/" 開頭         → 指令處理（menu_handler）
    """
    last_update_id = state.get("last_update_id", 0)
    updates = sender.get_updates(offset=last_update_id + 1)
    if not updates:
        return

    new_id = last_update_id
    for update in updates:
        uid = update.get("update_id", 0)
        if uid > new_id:
            new_id = uid

        # ── Callback Query ──
        cq = update.get("callback_query")
        if cq:
            cb_data = cq.get("data", "")
            if cb_data.startswith("m:"):
                # 主控面板選單回呼
                try:
                    from menu_handler import handle_menu_callback
                    handle_menu_callback(sender, cq, rbac, tm, state)
                except Exception as exc:
                    print(f"⚠️ Menu callback error: {exc}")
                    sender.answer_callback(cq.get("id", ""), f"❌ {exc}")
            elif cb_data == "/restart":
                # 舊版告警重啟按鈕（向後相容）
                _handle_legacy_restart(sender, cq, state, rbac)
            elif cb_data in ("/logs", "/health", "/tasks", "/perf"):
                # 舊版告警資訊按鈕 → 回應對應內容
                _handle_legacy_info(sender, cq, cb_data)
            elif cb_data.startswith("/exec "):
                # 安全指令執行（僅允許白名單）
                _handle_safe_exec(sender, cq, cb_data)
            else:
                sender.answer_callback(cq.get("id", ""), "此功能開發中")
            continue

        # ── Message（指令）──
        msg = update.get("message")
        if msg:
            text = (msg.get("text") or "").strip()
            if text.startswith("/"):
                try:
                    from menu_handler import handle_command
                    handle_command(sender, msg, rbac, tm, state)
                except Exception as exc:
                    print(f"⚠️ Command error: {exc}")

    state["last_update_id"] = new_id


def _handle_legacy_restart(sender: TelegramSender, cq: dict, state: dict, rbac):
    """處理舊版告警按鈕的 /restart 回呼（完整保留原有邏輯）"""
    cb_id = cq.get("id")
    from_info = cq.get("from", {})
    from_user_id = str(from_info.get("id", ""))
    from_username = from_info.get("username", "unknown")
    chat_id = str(cq.get("message", {}).get("chat", {}).get("id", sender.chat_id))
    tenant_id = f"telegram:{chat_id}"

    # RBAC 權限檢查
    perm = rbac.check_permission(from_user_id, tenant_id, "restart_gateway")
    if not perm.allowed:
        sender.answer_callback(cb_id, f"⛔ 權限不足: {perm.reason}")
        try:
            from audit import audit_permission_denied
            audit_permission_denied(tenant_id, from_user_id, from_username, "restart_gateway", perm.reason)
        except Exception:
            pass
        print(f"⛔ @{from_username} 重啟被拒: {perm.reason}")
        return

    print(f"🔄 收到來自 @{from_username} 的重啟請求（已授權）")
    sender.answer_callback(cb_id, "正在重啟 Gateway...")

    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
    try:
        r = subprocess.run(
            ["systemctl", "--user", "restart", "openclaw-gateway"],
            capture_output=True, text=True, timeout=15, env=env,
        )
        if r.returncode == 0:
            sender.send("🔄 <b>Gateway 重啟中</b>\n請稍候約 1 分鐘，系統會自動發送重啟完成通知")
            reset_self_heal_on_recovery(state)
            result = "success"
        else:
            sender.send(f"❌ Gateway 重啟失敗\n{r.stderr}")
            result = "failed"
    except Exception as exc:
        sender.send(f"❌ 執行重啟時發生錯誤: {exc}")
        result = "error"

    try:
        from audit import audit_restart
        audit_restart(tenant_id, from_user_id, from_username, "button", result)
    except Exception:
        pass


def _handle_legacy_info(sender: TelegramSender, cq: dict, cb_data: str):
    """處理舊版告警按鈕的資訊回呼（/logs, /health, /tasks, /perf）"""
    from telegram_ui import (
        truncate, generate_gateway_logs, generate_health_check, generate_perf_detail,
    )
    cb_id = cq.get("id", "")

    if cb_data == "/logs":
        text = generate_gateway_logs()
    elif cb_data == "/health":
        text = generate_health_check()
    elif cb_data in ("/tasks", "/perf"):
        text = generate_perf_detail()
    else:
        sender.answer_callback(cb_id, "此功能開發中")
        return

    sender.answer_callback(cb_id)
    sender.send(truncate(text))


def _handle_safe_exec(sender: TelegramSender, cq: dict, cb_data: str):
    """處理安全指令執行（僅允許白名單指令，需 admin 權限）"""
    cb_id = cq.get("id", "")
    from_info = cq.get("from", {})
    from_user_id = str(from_info.get("id", ""))
    chat_id = str(cq.get("message", {}).get("chat", {}).get("id", sender.chat_id))
    tenant_id = f"telegram:{chat_id}"

    # RBAC 權限檢查
    rbac = _get_rbac_manager()
    perm = rbac.check_permission(from_user_id, tenant_id, "exec_command")
    if not perm.allowed:
        sender.answer_callback(cb_id, f"⛔ {perm.reason}")
        return

    cmd = cb_data[6:].strip()  # 去掉 "/exec "

    SAFE_COMMANDS = {"df -h", "uptime", "free -h"}
    if cmd not in SAFE_COMMANDS:
        sender.answer_callback(cb_id, "此指令不允許執行")
        return

    try:
        out = subprocess.check_output(cmd.split(), text=True, timeout=10)
        text = f"<b>📋 {cmd}</b>\n\n<code>{out[:3500]}</code>"
    except Exception as e:
        text = f"❌ 執行失敗: {e}"

    sender.answer_callback(cb_id)
    from telegram_ui import truncate
    sender.send(truncate(text))


# ─── /monitor 快照（供 SOUL.md 或 skill 使用）───────────

def get_monitor_snapshot_text() -> str:
    """讀取 monitoring_state.json 並回傳可直接顯示的文字（給 /monitor 指令用）"""
    state = load_state()
    return render_dashboard(state)


# ─── 主程式 ───────────────────────────────────────────────

def main() -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN 未設定")
        return 1

    # ── 載入租戶 ──
    tm = _get_tenant_manager()
    rbac = _get_rbac_manager()  # 確保 RBAC 初始化（含遷移）
    tenants = tm.get_active_tenants()
    if not tenants:
        # 回退：無租戶時用 .env 的 chat_id
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if chat_id:
            tenants = [tm.register(chat_id, "Admin (Primary)")]
        else:
            print("❌ 無已註冊租戶且 TELEGRAM_CHAT_ID 未設定")
            return 1

    # ── 1. 平行採集（全域一次）──
    t0 = time.monotonic()
    snap = collect_all_parallel()
    collect_ms = int((time.monotonic() - t0) * 1000)
    print(f"📡 採集完成 ({collect_ms}ms)")

    # ── 2. 健康分數（全域一次）──
    score, grade = compute_health_score(snap)

    # ── 3. 全域快照（向後相容 + /monitor）──
    tm.save_global_snapshot(snap, score, grade)
    # 同時寫入舊格式 monitoring_state.json（向後相容 monitor_snapshot.py）
    _save_compat_global_state(snap, score, grade)

    # ── 4. 全域自癒（Gateway 是系統資源，只做一次）──
    gw_now = snap.get("gateway_active", True)
    global_heal_msg = None
    primary_tenant = tenants[0]
    primary_state = tm.load_tenant_state(primary_tenant)

    if not gw_now:
        global_heal_msg = try_self_heal_gateway(primary_state)
        if global_heal_msg:
            print(f"🔧 {global_heal_msg}")
            record_error(primary_state, "self_heal", "gateway", global_heal_msg, severity="info")
            try:
                from audit import audit_log as _audit_global
                _audit_global(primary_tenant.tenant_id, "self_heal", detail=global_heal_msg)
            except Exception:
                pass

    # 如果 Gateway 恢復，重設自癒計數
    if gw_now and not primary_state.get("gateway_prev_running", True):
        reset_self_heal_on_recovery(primary_state)

    # ── 4b. 處理所有 Telegram 更新（指令 + 選單回呼 + 告警按鈕）──
    sender_for_updates = TelegramSender(token, primary_tenant.chat_id)
    _ensure_bot_commands(sender_for_updates, primary_state)
    _process_updates(sender_for_updates, primary_state, gw_now, tm, rbac)

    tm.save_tenant_state(primary_tenant, primary_state)

    # ── 4c. Token 成本追蹤（增量掃描 + 預算告警）──
    token_summary = None
    try:
        from token_governance import run_token_check
        _budget_alerts, token_summary = run_token_check(sender_for_updates)
        if _budget_alerts:
            print(f"💰 Token 預算告警: {len(_budget_alerts)} 則")
    except Exception as _te:
        print(f"⚠️ Token 追蹤失敗: {_te}")

    # ── 5. 逐租戶分發告警與儀表板 ──
    total_alerts_sent = 0
    for tenant in tenants:
        sent = _process_tenant(token, tenant, tm, snap, score, grade, gw_now, global_heal_msg, token_summary)
        total_alerts_sent += sent

    if total_alerts_sent == 0:
        print(f"✅ 系統正常 (健康分數: {score}/{grade}, 租戶: {len(tenants)})")
    else:
        print(f"🔔 共發送 {total_alerts_sent} 則警報 (健康分數: {score}/{grade}, 租戶: {len(tenants)})")
    return 0


def _process_tenant(token: str, tenant, tm, snap: dict, score: int, grade: str,
                    gw_now: bool, global_heal_msg: str = None,
                    token_summary: dict = None) -> int:
    """
    處理單一租戶：告警 + 儀表板更新。
    自癒已在全域 main() 中處理，此處僅負責告警分發與儀表板。
    回傳發送的告警數量。
    """
    # 租戶設定檢查
    if not tenant.get_setting("alerts_enabled", True) and not tenant.get_setting("dashboard_enabled", True):
        return 0

    state = tm.load_tenant_state(tenant)
    sender = TelegramSender(token, tenant.chat_id)
    alerts_sent = 0

    # 讀取每日會話統計
    snap_with_sessions = dict(snap)
    snap_with_sessions["sessions_today"] = state.get("snapshot", {}).get("sessions_today", 0)
    snap_with_sessions["sessions_completed"] = state.get("snapshot", {}).get("sessions_completed", 0)
    snap_with_sessions["sessions_failed"] = state.get("snapshot", {}).get("sessions_failed", 0)

    # ── 告警 ──
    if tenant.get_setting("alerts_enabled", True):
        # 使用租戶自訂閾值
        tenant_thresholds = {
            "cpu_percent": tenant.get_setting("thresholds.cpu_percent", THRESHOLDS["cpu_percent"]),
            "memory_percent": tenant.get_setting("thresholds.memory_percent", THRESHOLDS["memory_percent"]),
            "disk_percent": tenant.get_setting("thresholds.disk_percent", THRESHOLDS["disk_percent"]),
            "load_avg_1m": tenant.get_setting("thresholds.load_avg_1m", THRESHOLDS["load_avg_1m"]),
        }
        alert_events = evaluate_alerts(snap_with_sessions, state, thresholds=tenant_thresholds)

        # 使用租戶自訂冷卻時間
        tenant_cooldowns = {}
        for alert_type in ALERT_COOLDOWN:
            tenant_cooldowns[alert_type] = tenant.get_setting(
                f"alert_cooldowns.{alert_type}", ALERT_COOLDOWN[alert_type]
            )

        last_sent = state.setdefault("alerts", {}).setdefault("last_sent", {})
        to_send = _filter_with_tenant_cooldowns(alert_events, last_sent, tenant_cooldowns)

        for evt in to_send:
            severity_icon = "🚨" if evt.severity == "critical" else "⚠️"
            text = (
                f"{severity_icon} <b>系統警報</b>\n"
                f"{'━' * 25}\n"
                f"{evt.title}\n\n"
                f"{evt.detail}\n\n"
                f"<code>時間: {now_ts()} GMT+8</code>\n"
                f"<code>嚴重度: {evt.severity.upper()}</code>\n"
                f"<code>健康分數: {score}/100 ({grade})</code>"
            )
            if global_heal_msg:
                text += f"\n\n🔧 <b>自癒:</b> {global_heal_msg}"

            keyboard = build_keyboard(evt.alert_type) if tenant.get_setting("features.restart_button", True) else []
            msg_id = sender.send(text, keyboard=keyboard)
            if msg_id:
                last_sent[evt.alert_type] = now_iso()
                alerts_sent += 1

            record_error(state, evt.alert_type, "system", evt.detail, severity=evt.severity)

        active_alerts = [
            {"alert_type": e.alert_type, "severity": e.severity, "title": e.title, "timestamp": e.timestamp}
            for e in alert_events
        ]
        state.setdefault("alerts", {})["active_alerts"] = active_alerts

    # ── 儀表板 ──
    if tenant.get_setting("dashboard_enabled", True):
        state["snapshot"] = snap_with_sessions
        state["health_score"] = score
        state["health_grade"] = grade
        state["last_updated"] = now_ts()
        state["gateway_prev_running"] = gw_now

        dashboard_text = render_dashboard(state)
        msg_id = state.get("dashboard_message_id")
        try:
            if msg_id:
                ok = sender.edit(int(msg_id), dashboard_text)
                if not ok:
                    new_id = sender.send(dashboard_text)
                    state["dashboard_message_id"] = new_id
            else:
                new_id = sender.send(dashboard_text)
                state["dashboard_message_id"] = new_id
        except Exception:
            new_id = sender.send(dashboard_text)
            state["dashboard_message_id"] = new_id

    # ── 儲存租戶狀態 ──
    tm.save_tenant_state(tenant, state)
    return alerts_sent


def _filter_with_tenant_cooldowns(events, last_sent, cooldowns):
    """使用租戶自訂冷卻時間過濾告警"""
    now = datetime.now(TZ_GMT8)
    filtered = []
    for evt in events:
        cooldown = cooldowns.get(evt.alert_type, 600)
        last_ts_str = last_sent.get(evt.alert_type)
        if last_ts_str:
            try:
                last_dt = datetime.fromisoformat(last_ts_str)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=TZ_GMT8)
                if (now - last_dt).total_seconds() < cooldown:
                    continue
            except Exception:
                pass
        filtered.append(evt)
    return filtered


def _save_compat_global_state(snap: dict, score: int, grade: str):
    """向後相容：寫入精簡版 monitoring_state.json，僅含快照資訊供 monitor_snapshot.py 讀取。
    告警/自癒/錯誤等狀態已移至各租戶目錄，不再寫入全域檔。"""
    data = {
        "version": 2,
        "last_updated": now_ts(),
        "health_score": score,
        "health_grade": grade,
        "snapshot": snap,
        "gateway_prev_running": snap.get("gateway_active", True),
        "multi_tenant": True,
    }
    # 僅保留 dashboard_message_id 供 snapshot 腳本參考
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                old = json.load(f)
            if "dashboard_message_id" in old:
                data["dashboard_message_id"] = old["dashboard_message_id"]
        except Exception:
            pass
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def _migrate_legacy_state(state: dict):
    """從舊版狀態檔案遷移資料（僅在 version < 2 或首次建立時執行）"""
    if state.get("version") == 2 and state.get("last_update_id", 0) > 0:
        return  # 已遷移過

    # 遷移 proactive_alert_state.json
    old_alert = "/root/.openclaw/monitoring/proactive_alert_state.json"
    if os.path.exists(old_alert):
        try:
            with open(old_alert, "r") as f:
                old = json.load(f)
            if old.get("last_update_id") and old["last_update_id"] > state.get("last_update_id", 0):
                state["last_update_id"] = old["last_update_id"]
            if old.get("last_alerts"):
                state.setdefault("alerts", {}).setdefault("last_sent", {}).update(old["last_alerts"])
            if "last_status" in old:
                state["gateway_prev_running"] = old["last_status"].get("gateway_running", True)
        except Exception:
            pass

    # 遷移 unified_dashboard_state.json
    old_dash = "/root/.openclaw/monitoring/unified_dashboard_state.json"
    if os.path.exists(old_dash):
        try:
            with open(old_dash, "r") as f:
                old = json.load(f)
            if old.get("dashboard_message_id") and not state.get("dashboard_message_id"):
                state["dashboard_message_id"] = old["dashboard_message_id"]
            history = old.get("history", {})
            if history:
                snap = state.setdefault("snapshot", {})
                snap["sessions_today"] = history.get("today_sessions", 0)
                snap["sessions_completed"] = history.get("completed_sessions", 0)
                snap["sessions_failed"] = history.get("failed_sessions", 0)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
