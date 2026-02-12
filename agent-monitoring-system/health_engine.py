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
    v = sh("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
    try:
        return {"cpu_percent": float(v)}
    except ValueError:
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


def evaluate_alerts(snap: dict, state: dict) -> List[AlertEvent]:
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
    if cpu > THRESHOLDS["cpu_percent"]:
        events.append(AlertEvent(
            alert_type="cpu_high",
            severity="critical" if cpu > 95 else "warning",
            title="⚠️ CPU 使用率過高",
            detail=f"目前 CPU: <b>{cpu:.1f}%</b> (閾值: {THRESHOLDS['cpu_percent']}%)",
        ))

    # Memory
    mem = snap.get("memory_percent", 0)
    if mem > THRESHOLDS["memory_percent"]:
        events.append(AlertEvent(
            alert_type="memory_high",
            severity="critical" if mem > 95 else "warning",
            title="⚠️ 記憶體使用率過高",
            detail=f"目前記憶體: <b>{mem:.1f}%</b> (閾值: {THRESHOLDS['memory_percent']}%)",
        ))

    # Disk
    disk = snap.get("disk_percent", 0)
    if disk > THRESHOLDS["disk_percent"]:
        events.append(AlertEvent(
            alert_type="disk_high",
            severity="critical" if disk > 95 else "warning",
            title="🗄️ 磁碟空間不足",
            detail=f"目前磁碟使用: <b>{disk:.1f}%</b> (閾值: {THRESHOLDS['disk_percent']}%)",
        ))

    # Load
    load_val = snap.get("load_1m", 0)
    if load_val > THRESHOLDS["load_avg_1m"]:
        events.append(AlertEvent(
            alert_type="load_high",
            severity="warning",
            title="📈 系統負載過高",
            detail=f"1 分鐘負載: <b>{load_val:.2f}</b> (閾值: {THRESHOLDS['load_avg_1m']})",
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

    def edit(self, message_id: int, text: str) -> bool:
        payload = {
            "chat_id": self.chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
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

    def get_updates(self, offset: int = 0) -> list:
        try:
            r = requests.post(
                f"{self.base}/getUpdates",
                json={"offset": offset, "timeout": 0, "allowed_updates": ["callback_query"]},
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


# ─── 重啟按鈕處理 ────────────────────────────────────────

def handle_restart_callbacks(sender: TelegramSender, state: dict):
    """只在 Gateway 停止時處理重啟按鈕"""
    last_update_id = state.get("last_update_id", 0)
    updates = sender.get_updates(offset=last_update_id + 1)
    if not updates:
        return

    new_id = last_update_id
    for update in updates:
        uid = update.get("update_id", 0)
        if uid > new_id:
            new_id = uid

        cq = update.get("callback_query")
        if not cq:
            continue

        cb_id = cq.get("id")
        cb_data = cq.get("data", "")
        from_user = cq.get("from", {}).get("username", "unknown")

        if cb_data == "/restart":
            print(f"🔄 收到來自 @{from_user} 的重啟請求")
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
                    # 重設自癒計數
                    reset_self_heal_on_recovery(state)
                else:
                    sender.send(f"❌ Gateway 重啟失敗\n{r.stderr}")
            except Exception as exc:
                sender.send(f"❌ 執行重啟時發生錯誤: {exc}")
        else:
            sender.answer_callback(cb_id, "此功能需要 Gateway 運行")

    state["last_update_id"] = new_id


# ─── /monitor 快照（供 SOUL.md 或 skill 使用）───────────

def get_monitor_snapshot_text() -> str:
    """讀取 monitoring_state.json 並回傳可直接顯示的文字（給 /monitor 指令用）"""
    state = load_state()
    return render_dashboard(state)


# ─── 主程式 ───────────────────────────────────────────────

def main() -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未設定")
        return 1

    state = load_state()

    # ── 遷移舊狀態 ──
    _migrate_legacy_state(state)

    sender = TelegramSender(token, chat_id)

    # ── 1. 平行採集 ──
    t0 = time.monotonic()
    snap = collect_all_parallel()
    collect_ms = int((time.monotonic() - t0) * 1000)
    print(f"📡 採集完成 ({collect_ms}ms)")

    # 讀取每日會話統計（繼承舊 dashboard 的 history）
    snap["sessions_today"] = state.get("snapshot", {}).get("sessions_today", 0)
    snap["sessions_completed"] = state.get("snapshot", {}).get("sessions_completed", 0)
    snap["sessions_failed"] = state.get("snapshot", {}).get("sessions_failed", 0)

    # ── 2. 健康分數 ──
    score, grade = compute_health_score(snap)

    # ── 3. 告警判斷 ──
    alert_events = evaluate_alerts(snap, state)

    # Gateway 狀態追蹤
    gw_now = snap.get("gateway_active", True)
    gw_prev = state.get("gateway_prev_running", True)

    # 如果 Gateway 恢復，重設自癒計數
    if gw_now and not gw_prev:
        reset_self_heal_on_recovery(state)

    # ── 4. 自癒 ──
    heal_msg = None
    if not gw_now:
        heal_msg = try_self_heal_gateway(state)
        if heal_msg:
            print(f"🔧 {heal_msg}")
            record_error(state, "self_heal", "gateway", heal_msg, severity="info")

    # ── 5. 冷卻過濾並發送告警 ──
    last_sent = state.setdefault("alerts", {}).setdefault("last_sent", {})
    to_send = filter_cooled_alerts(alert_events, last_sent)

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
        if heal_msg:
            text += f"\n\n🔧 <b>自癒:</b> {heal_msg}"

        keyboard = build_keyboard(evt.alert_type)
        msg_id = sender.send(text, keyboard=keyboard)
        if msg_id:
            last_sent[evt.alert_type] = now_iso()
            print(f"🔔 已發送 {evt.alert_type} 警報 (msg_id={msg_id})")

        # 記錄到錯誤追蹤
        record_error(state, evt.alert_type, "system", evt.detail, severity=evt.severity)

    # 更新活躍告警列表
    active_alerts = [asdict(e) if hasattr(e, '__dataclass_fields__') else
                     {"alert_type": e.alert_type, "severity": e.severity, "title": e.title, "timestamp": e.timestamp}
                     for e in alert_events]
    state.setdefault("alerts", {})["active_alerts"] = active_alerts

    # ── 6. Gateway 停止時處理重啟按鈕 ──
    if not gw_now:
        handle_restart_callbacks(sender, state)

    # ── 7. 更新儀表板訊息 ──
    state["snapshot"] = snap
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

    # ── 8. 儲存狀態 ──
    save_state(state)

    if not to_send:
        print(f"✅ 系統正常 (健康分數: {score}/{grade})")
    else:
        print(f"🔔 已發送 {len(to_send)} 則警報 (健康分數: {score}/{grade})")
    return 0


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
