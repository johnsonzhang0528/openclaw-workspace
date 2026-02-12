#!/usr/bin/env python3
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import requests

ACTIVE_WINDOW_MINUTES = 5
STATE_FILE = "/root/.openclaw/monitoring/unified_dashboard_state.json"
ENV_FILE = "/root/.openclaw/workspace/agent-monitoring-system/.env"


def load_env_file() -> None:
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file()

from data_store import SessionData, SessionStatus
from telegram_dashboard import TelegramDashboard


def ensure_state_dir() -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)


def load_state() -> Dict[str, Any]:
    ensure_state_dir()
    if not os.path.exists(STATE_FILE):
        return {
            "dashboard_message_id": None,
            "known_sessions": {},
            "history": {
                "today_sessions": 0,
                "completed_sessions": 0,
                "failed_sessions": 0,
                "total_runtime_minutes": 0.0,
            },
            "last_reset_date": datetime.now().strftime("%Y-%m-%d"),
        }
    with open(STATE_FILE, "r", encoding="utf-8") as state_file:
        return json.load(state_file)


def save_state(state: Dict[str, Any]) -> None:
    ensure_state_dir()
    with open(STATE_FILE, "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=2, ensure_ascii=False)


def extract_task_description(session_id: str) -> Optional[str]:
    """從會話文件中提取用戶的任務描述（第一個 user 消息）"""
    session_file = f"/root/.openclaw/agents/main/sessions/{session_id}.jsonl"
    if not os.path.exists(session_file):
        return None
    
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") != "message":
                        continue
                    message = entry.get("message", {})
                    if message.get("role") != "user":
                        continue
                    content = message.get("content", [])
                    if not content:
                        continue
                    text = content[0].get("text", "")
                    # 移除時間戳前綴
                    if text.startswith("["):
                        parts = text.split("]", 1)
                        if len(parts) > 1:
                            text = parts[1].strip()
                    # 截取前 80 字符
                    if len(text) > 80:
                        text = text[:77] + "..."
                    return text if text else None
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return None


def parse_task_label(session_key: str, session_id: str, index: int) -> str:
    if ":subagent:" in session_key:
        identifier = session_key.split(":subagent:", 1)[1][:8]
        task_desc = extract_task_description(session_id)
        if task_desc:
            return f"子代理任務 #{index} ({identifier}): {task_desc}"
        return f"子代理任務 #{index} ({identifier})"
    return f"子代理任務 #{index}"


def calculate_progress(age_ms: int, total_tokens: Optional[int], context_tokens: Optional[int]) -> float:
    age_ratio = min(0.9, age_ms / float(ACTIVE_WINDOW_MINUTES * 60 * 1000))
    token_ratio = 0.0
    if total_tokens and context_tokens and context_tokens > 0:
        token_ratio = min(1.0, total_tokens / float(context_tokens))
    progress = min(0.95, max(age_ratio, token_ratio * 0.7))
    return max(0.05, progress)


def fetch_subagent_sessions() -> Dict[str, Any]:
    command = ["openclaw", "sessions", "list", "--json", "--kinds", "subagent"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return {"sessions": []}
    return json.loads(result.stdout)


def collect_system_metrics() -> SimpleNamespace:
    def run_shell(command: str) -> float:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        value = result.stdout.strip()
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    cpu_percent = run_shell("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
    memory_percent = run_shell("free | grep Mem | awk '{print $3/$2 * 100.0}'")
    disk_percent = run_shell("df -h / | tail -1 | awk '{print $5}' | sed 's/%//'")
    load_avg_1m = run_shell("cat /proc/loadavg | awk '{print $1}'")

    return SimpleNamespace(
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        disk_percent=disk_percent,
        network_sent_mb=0.0,
        network_recv_mb=0.0,
        load_avg_1m=load_avg_1m,
    )


@dataclass
class MonitoringSnapshot:
    active_sessions: List[SessionData]
    all_subagent_total: int
    alerts: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    known_sessions: Dict[str, Any]


class OpenClawSessionAdapter:
    def __init__(self, state: Dict[str, Any]):
        self.state = state
        self.active_sessions: List[SessionData] = []
        self.total_subagent_sessions = 0
        self.statistics = {
            "today_sessions": 0,
            "completed_sessions": 0,
            "failed_sessions": 0,
            "avg_runtime_minutes": 0.0,
            "success_rate": 0.0,
        }
        self.alerts: List[Dict[str, Any]] = []

    def refresh(self) -> MonitoringSnapshot:
        sessions_payload = fetch_subagent_sessions()
        sessions = sessions_payload.get("sessions", [])
        self.total_subagent_sessions = len(sessions)

        now = datetime.now()
        active_cutoff_ms = ACTIVE_WINDOW_MINUTES * 60 * 1000

        previous_known = self.state.get("known_sessions", {})
        new_known: Dict[str, Any] = {}

        daily_state = self.state.get("history", {})
        today = now.strftime("%Y-%m-%d")
        if self.state.get("last_reset_date") != today:
            daily_state = {
                "today_sessions": 0,
                "completed_sessions": 0,
                "failed_sessions": 0,
                "total_runtime_minutes": 0.0,
            }
            self.state["last_reset_date"] = today

        active_items = []
        alerts: List[Dict[str, Any]] = []
        seen_ids = set()

        for index, session in enumerate(sessions, start=1):
            key = str(session.get("key", ""))
            if ":subagent:" not in key:
                continue

            session_id = str(session.get("sessionId", ""))
            if not session_id:
                continue
            seen_ids.add(session_id)

            age_ms = int(session.get("ageMs", 10**9) or 10**9)
            is_active = age_ms <= active_cutoff_ms
            aborted = bool(session.get("abortedLastRun", False))

            new_known[session_id] = {
                "key": key,
                "last_seen": now.isoformat(),
                "age_ms": age_ms,
                "abortedLastRun": aborted,
            }

            if aborted:
                alerts.append(
                    {
                        "timestamp": now,
                        "severity": "critical",
                        "message": f"子代理異常終止: {key}",
                    }
                )

            if not is_active:
                continue

            total_tokens = session.get("totalTokens")
            context_tokens = session.get("contextTokens")
            progress = calculate_progress(age_ms, total_tokens, context_tokens)

            start_time = now - timedelta(milliseconds=age_ms)
            estimated_completion = now + timedelta(minutes=max(1, ACTIVE_WINDOW_MINUTES - int(age_ms / 60000)))

            active_items.append(
                SessionData(
                    session_id=session_id,
                    label=parse_task_label(key, session_id, index),
                    status=SessionStatus.ACTIVE,
                    progress=progress,
                    start_time=start_time,
                    last_update=now,
                    estimated_completion=estimated_completion,
                    metadata={
                        "key": key,
                        "model": session.get("model", "unknown"),
                        "tokens": total_tokens or 0,
                    },
                )
            )

        for session_id, snapshot in previous_known.items():
            if session_id in seen_ids:
                continue
            last_seen = snapshot.get("last_seen")
            if not last_seen:
                continue
            try:
                last_seen_dt = datetime.fromisoformat(last_seen)
            except ValueError:
                continue

            if (now - last_seen_dt) <= timedelta(minutes=2):
                if bool(snapshot.get("abortedLastRun", False)):
                    daily_state["failed_sessions"] = int(daily_state.get("failed_sessions", 0)) + 1
                else:
                    daily_state["completed_sessions"] = int(daily_state.get("completed_sessions", 0)) + 1
                daily_state["total_runtime_minutes"] = float(daily_state.get("total_runtime_minutes", 0.0)) + (
                    float(snapshot.get("age_ms", 0)) / 60000.0
                )

        known_count_before = len(previous_known)
        known_count_now = len(new_known)
        if known_count_now > known_count_before:
            daily_state["today_sessions"] = int(daily_state.get("today_sessions", 0)) + (known_count_now - known_count_before)

        completed = int(daily_state.get("completed_sessions", 0))
        failed = int(daily_state.get("failed_sessions", 0))
        total_ended = completed + failed
        success_rate = (completed / total_ended * 100.0) if total_ended else 100.0
        avg_runtime = (float(daily_state.get("total_runtime_minutes", 0.0)) / completed) if completed else 0.0

        self.statistics = {
            "today_sessions": int(daily_state.get("today_sessions", 0)),
            "completed_sessions": completed,
            "failed_sessions": failed,
            "avg_runtime_minutes": avg_runtime,
            "success_rate": success_rate,
        }

        if len(active_items) == 0:
            alerts.append(
                {
                    "timestamp": now,
                    "severity": "warning",
                    "message": "目前沒有活躍子代理任務",
                }
            )

        self.active_sessions = sorted(active_items, key=lambda item: item.last_update, reverse=True)
        self.alerts = alerts

        self.state["known_sessions"] = new_known
        self.state["history"] = daily_state

        return MonitoringSnapshot(
            active_sessions=self.active_sessions,
            all_subagent_total=self.total_subagent_sessions,
            alerts=self.alerts,
            statistics=self.statistics,
            known_sessions=new_known,
        )

    def get_active_sessions(self, limit: int = 10) -> List[SessionData]:
        return self.active_sessions[:limit]

    def get_session_count(self) -> int:
        return self.total_subagent_sessions

    def get_statistics(self) -> Dict[str, Any]:
        return self.statistics

    def get_session(self, session_id: str) -> Optional[SessionData]:
        for session in self.active_sessions:
            if session.session_id == session_id:
                return session
        return None


class LightweightResourceMonitor:
    def __init__(self):
        self.current = collect_system_metrics()

    def refresh(self) -> None:
        self.current = collect_system_metrics()

    def get_current_metrics(self):
        return self.current


class TelegramEditor:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str) -> int:
        response = requests.post(
            f"{self.base_url}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"sendMessage failed: {payload}")
        return int(payload["result"]["message_id"])

    def edit_message(self, message_id: int, text: str) -> bool:
        response = requests.post(
            f"{self.base_url}/editMessageText",
            json={
                "chat_id": self.chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return bool(payload.get("ok"))


def build_dashboard(state: Dict[str, Any]) -> str:
    tracker = OpenClawSessionAdapter(state)
    snapshot = tracker.refresh()

    resource_monitor = LightweightResourceMonitor()
    resource_monitor.refresh()

    dashboard = TelegramDashboard(tracker, resource_monitor)
    text = dashboard.generate_full_dashboard(snapshot.alerts)

    header = (
        "<b>📌 統一監控版塊（固定同一則訊息）</b>\n"
        f"<code>活躍判定: {ACTIVE_WINDOW_MINUTES} 分鐘內</code>\n"
        f"<code>更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
        f"<code>總子代理會話: {snapshot.all_subagent_total}</code>\n"
        "<code>模式: 只追蹤活躍任務 + 異常即時標記</code>\n"
        + ("=" * 35)
        + "\n"
    )

    output = header + text
    if len(output) > 3900:
        output = output[:3850] + "\n<code>...內容過長已截斷</code>"
    return output


def main() -> int:
    load_env_file()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未設定")
        return 1

    state = load_state()
    dashboard_text = build_dashboard(state)
    editor = TelegramEditor(bot_token, chat_id)

    message_id = state.get("dashboard_message_id")
    try:
        if message_id:
            ok = editor.edit_message(int(message_id), dashboard_text)
            if not ok:
                new_message_id = editor.send_message(dashboard_text)
                state["dashboard_message_id"] = new_message_id
        else:
            new_message_id = editor.send_message(dashboard_text)
            state["dashboard_message_id"] = new_message_id
    except Exception:
        new_message_id = editor.send_message(dashboard_text)
        state["dashboard_message_id"] = new_message_id

    save_state(state)
    print("✅ Unified dashboard updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
