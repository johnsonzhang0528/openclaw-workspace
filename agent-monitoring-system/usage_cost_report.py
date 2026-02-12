#!/usr/bin/env python3
"""
API 使用量與費用自動報告
每日 21:00 (GMT+8) 自動生成，使用「編輯同一則訊息」模式
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

TZ_GMT8 = timezone(timedelta(hours=8))
STATE_FILE = "/root/.openclaw/monitoring/usage_report_state.json"
ENV_FILE = "/root/.openclaw/workspace/agent-monitoring-system/.env"
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions")


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
        return {"message_id": None, "date": None, "history": []}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ─── OpenClaw Usage 取得 ──────────────────────────────────

def get_openclaw_usage() -> dict:
    """透過 openclaw CLI 取得使用量資訊"""
    try:
        result = subprocess.run(
            ["openclaw", "usage", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception:
        pass

    # fallback: 嘗試從 session 檔案統計
    return estimate_usage_from_sessions()


def estimate_usage_from_sessions() -> dict:
    """從 session 檔案估算使用量"""
    now = datetime.now(TZ_GMT8)
    today = now.strftime("%Y-%m-%d")
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_write = 0
    total_cost_usd = 0.0
    session_count = 0
    model_usage: dict[str, int] = {}

    if not SESSIONS_DIR.exists():
        return {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cache_read_tokens": 0,
            "total_cache_write_tokens": 0,
            "session_count": 0,
            "model_usage": {},
            "estimated": True,
        }

    for session_file in SESSIONS_DIR.glob("*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=TZ_GMT8)
            if mtime.strftime("%Y-%m-%d") != today:
                continue

            session_count += 1
            with open(session_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("type") != "message":
                            continue
                        msg = entry.get("message", {})
                        usage = msg.get("usage", {})
                        if not usage or usage.get("totalTokens", 0) == 0:
                            continue
                        total_input += usage.get("input", 0)
                        total_output += usage.get("output", 0)
                        total_cache_read += usage.get("cacheRead", 0)
                        total_cache_write += usage.get("cacheWrite", 0)
                        cost = usage.get("cost", {})
                        total_cost_usd += cost.get("total", 0)
                        model = msg.get("model", "unknown")
                        model_usage[model] = model_usage.get(model, 0) + 1
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_read_tokens": total_cache_read,
        "total_cache_write_tokens": total_cache_write,
        "session_count": session_count,
        "model_usage": model_usage,
        "reported_cost_usd": total_cost_usd,
        "estimated": True,
    }


# ─── 費用計算 ─────────────────────────────────────────────

# DeepSeek 定價 (USD per 1M tokens) — 來源: DeepSeek 官方
PRICING = {
    "deepseek-chat": {
        "input": 0.27,       # $0.27 / 1M tokens (cache miss)
        "output": 1.10,      # $1.10 / 1M tokens
        "cache_read": 0.07,  # $0.07 / 1M tokens (cache hit)
    },
}


def calculate_cost(usage: dict) -> dict:
    input_tokens = usage.get("total_input_tokens", 0)
    output_tokens = usage.get("total_output_tokens", 0)
    cache_tokens = usage.get("total_cache_read_tokens", 0)

    pricing = PRICING.get("deepseek-chat", PRICING["deepseek-chat"])

    # DeepSeek: input = cache miss tokens, cacheRead = cache hit tokens
    # 兩者分開計費
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    cache_cost = (cache_tokens / 1_000_000) * pricing["cache_read"]

    # 如果 session 有回報 cost，優先使用
    reported = usage.get("reported_cost_usd", 0)
    total = reported if reported > 0 else (input_cost + output_cost + cache_cost)

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "cache_cost": cache_cost,
        "total_cost": total,
        "currency": "USD",
    }


# ─── 歷史趨勢 ─────────────────────────────────────────────

def get_trend(history: list, key: str = "total_cost") -> str:
    if len(history) < 2:
        return "📊 數據不足，尚無趨勢"
    recent = [h.get(key, 0) for h in history[-7:]]
    if len(recent) < 2:
        return "📊 數據不足"
    avg = sum(recent) / len(recent)
    last = recent[-1]
    if avg == 0:
        return "📊 持平"
    diff_pct = ((last - avg) / avg) * 100
    if diff_pct > 10:
        return f"📈 上升 {diff_pct:+.1f}% (相較 7 日平均)"
    elif diff_pct < -10:
        return f"📉 下降 {diff_pct:+.1f}% (相較 7 日平均)"
    else:
        return f"📊 持平 ({diff_pct:+.1f}%)"


# ─── 報告生成 ──────────────────────────────────────────────

def build_usage_report(usage: dict, cost: dict, history: list) -> str:
    now = datetime.now(TZ_GMT8)
    sections = []

    # Header
    estimated_tag = " (估算)" if usage.get("estimated") else ""
    sections.append(
        f"<b>💰 API 使用量與費用報告{estimated_tag}</b>\n"
        f"<code>日期: {now.strftime('%Y-%m-%d')}</code>\n"
        f"<code>生成時間: {now.strftime('%H:%M:%S')} GMT+8</code>\n"
        f"{'━' * 30}"
    )

    # Token 使用量
    total_tokens = usage.get("total_input_tokens", 0) + usage.get("total_output_tokens", 0)
    sections.append(
        f"\n<b>📊 Token 使用量</b>\n"
        f"  輸入 Tokens: <code>{usage.get('total_input_tokens', 0):,}</code>\n"
        f"  輸出 Tokens: <code>{usage.get('total_output_tokens', 0):,}</code>\n"
        f"  快取命中: <code>{usage.get('total_cache_read_tokens', 0):,}</code>\n"
        f"  總計: <code>{total_tokens:,}</code> tokens\n"
        f"  工作階段: <b>{usage.get('session_count', 0)}</b> 個"
    )

    # 費用明細
    sections.append(
        f"\n<b>💵 費用明細 (USD)</b>\n"
        f"  輸入成本: <code>${cost['input_cost']:.4f}</code>\n"
        f"  輸出成本: <code>${cost['output_cost']:.4f}</code>\n"
        f"  快取成本: <code>${cost['cache_cost']:.4f}</code>\n"
        f"  <b>今日總計: <code>${cost['total_cost']:.4f}</code></b>"
    )

    # 模型使用分布
    model_usage = usage.get("model_usage", {})
    if model_usage:
        model_section = "\n<b>🤖 模型使用分布</b>\n"
        for model, count in sorted(model_usage.items(), key=lambda x: -x[1]):
            model_section += f"  {model}: <b>{count}</b> 次呼叫\n"
        sections.append(model_section.rstrip())

    # 趨勢
    trend = get_trend(history, "total_cost")
    sections.append(f"\n<b>📈 費用趨勢</b>\n  {trend}")

    # 7 天歷史
    if history:
        hist_section = "\n<b>📅 近 7 日費用</b>\n"
        for h in history[-7:]:
            d = h.get("date", "?")
            c = h.get("total_cost", 0)
            t = h.get("total_tokens", 0)
            bar_len = min(15, max(1, int(c * 100)))  # 簡易視覺化
            bar = "█" * bar_len
            hist_section += f"  <code>{d}</code> ${c:.4f} ({t:,}t) {bar}\n"
        sections.append(hist_section.rstrip())

    # Footer
    sections.append(
        f"\n{'━' * 30}\n"
        f"<code>下次自動報告: 明日 21:00</code>"
    )

    text = "\n".join(sections)
    if len(text) > 3900:
        text = text[:3850] + "\n<code>...內容過長已截斷</code>"
    return text


# ─── Telegram 傳送 ────────────────────────────────────────

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

    def edit(self, mid: int, text: str) -> bool:
        r = requests.post(f"{self.base}/editMessageText", json={
            "chat_id": self.chat_id, "message_id": mid, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }, timeout=20)
        return r.json().get("ok", False)


# ─── 主程式 ───────────────────────────────────────────────

def main() -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未設定")
        return 1

    state = load_state()
    today = datetime.now(TZ_GMT8).strftime("%Y-%m-%d")

    # 取得使用量與費用
    usage = get_openclaw_usage()
    cost = calculate_cost(usage)

    # 更新歷史
    history = state.get("history", [])
    total_tokens = usage.get("total_input_tokens", 0) + usage.get("total_output_tokens", 0)
    today_entry = {
        "date": today,
        "total_cost": cost["total_cost"],
        "total_tokens": total_tokens,
        "sessions": usage.get("session_count", 0),
    }

    # 如果今天的紀錄已存在，更新它
    updated = False
    for i, h in enumerate(history):
        if h.get("date") == today:
            history[i] = today_entry
            updated = True
            break
    if not updated:
        history.append(today_entry)

    # 只保留最近 30 天
    history = history[-30:]

    report = build_usage_report(usage, cost, history)
    sender = TelegramSender(token, chat_id)

    msg_id = state.get("message_id")
    state_date = state.get("date")

    if state_date == today and msg_id:
        try:
            ok = sender.edit(int(msg_id), report)
            if not ok:
                raise RuntimeError("edit failed")
        except Exception:
            msg_id = sender.send(report)
            state["message_id"] = msg_id
    else:
        msg_id = sender.send(report)
        state["message_id"] = msg_id

    state["date"] = today
    state["history"] = history
    save_state(state)
    print(f"✅ Usage report sent/updated (msg_id={msg_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
