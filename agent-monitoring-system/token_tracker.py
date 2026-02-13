#!/usr/bin/env python3
"""
Token 追蹤器 (Token Tracker)
═════════════════════════════
職責：
  1. 即時掃描 Session JSONL 檔案，提取每次 API 呼叫的 token 用量
  2. 歸因分類：per-session、per-model、per-hour、per-day
  3. 成本計算：使用外部定價表（支援 DeepSeek、OpenAI 等）
  4. 增量掃描：只處理上次掃描後的新資料（offset-based）
  5. 持久化追蹤狀態至 token_tracker_state.json

資料來源：
  /root/.openclaw/agents/main/sessions/*.jsonl
  每條 type="message" 的記錄包含：
    message.usage.{input, output, cacheRead, cacheWrite, totalTokens}
    message.{model, provider, api}

不依賴 OpenClaw CLI（避免 CLI 不可用時失敗），直接解析 JSONL 檔案。
"""

import json
import os
import glob
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

TZ_GMT8 = timezone(timedelta(hours=8))

# ─── 路徑 ────────────────────────────────────────────────

SESSIONS_DIR = "/root/.openclaw/agents/main/sessions"
STATE_DIR = "/root/.openclaw/monitoring"
STATE_FILE = os.path.join(STATE_DIR, "token_tracker_state.json")

# ─── 定價表 (USD per 1M tokens) ────────────────────────

# DeepSeek V3 (deepseek-chat) 定價 — 來源: https://api-docs.deepseek.com/quick_start/pricing
# 2025-02-08 起生效
PRICING = {
    "deepseek-chat": {
        "input": 0.27,         # cache miss
        "output": 1.10,
        "cache_read": 0.07,    # cache hit
        "cache_write": 0.27,   # same as input
    },
    "deepseek-reasoner": {
        "input": 0.55,
        "output": 2.19,
        "cache_read": 0.14,
        "cache_write": 0.55,
    },
    # fallback: 使用 deepseek-chat 定價
    "_default": {
        "input": 0.27,
        "output": 1.10,
        "cache_read": 0.07,
        "cache_write": 0.27,
    },
}


def get_pricing(model: str) -> dict:
    """取得模型定價，未知模型使用 _default"""
    return PRICING.get(model, PRICING["_default"])


def calc_cost(model: str, usage: dict) -> dict:
    """計算單次 API 呼叫成本"""
    p = get_pricing(model)
    inp = usage.get("input", 0)
    out = usage.get("output", 0)
    cr = usage.get("cacheRead", 0)
    cw = usage.get("cacheWrite", 0)

    cost_input = (inp / 1_000_000) * p["input"]
    cost_output = (out / 1_000_000) * p["output"]
    cost_cache_read = (cr / 1_000_000) * p["cache_read"]
    cost_cache_write = (cw / 1_000_000) * p["cache_write"]
    total = cost_input + cost_output + cost_cache_read + cost_cache_write

    return {
        "input": round(cost_input, 6),
        "output": round(cost_output, 6),
        "cache_read": round(cost_cache_read, 6),
        "cache_write": round(cost_cache_write, 6),
        "total": round(total, 6),
    }


# ─── 資料結構 ────────────────────────────────────────────

@dataclass
class APICall:
    """單次 API 呼叫記錄"""
    session_id: str
    message_id: str
    timestamp: str            # ISO 8601
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_write: int
    total_tokens: int
    cost_usd: float


@dataclass
class HourlyBucket:
    """每小時聚合"""
    hour: str                 # "2026-02-13T14"
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, call: APICall):
        self.calls += 1
        self.input_tokens += call.input_tokens
        self.output_tokens += call.output_tokens
        self.cache_read += call.cache_read
        self.cache_write += call.cache_write
        self.total_tokens += call.total_tokens
        self.cost_usd += call.cost_usd


@dataclass
class DailyBucket:
    """每日聚合"""
    date: str                 # "2026-02-13"
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    sessions: int = 0
    models: Dict[str, int] = field(default_factory=dict)  # model → call count
    peak_hour: str = ""       # 最高用量的小時
    peak_hour_cost: float = 0.0

    def add(self, call: APICall):
        self.calls += 1
        self.input_tokens += call.input_tokens
        self.output_tokens += call.output_tokens
        self.cache_read += call.cache_read
        self.cache_write += call.cache_write
        self.total_tokens += call.total_tokens
        self.cost_usd += call.cost_usd
        self.models[call.model] = self.models.get(call.model, 0) + 1


# ─── 追蹤器 ──────────────────────────────────────────────

class TokenTracker:
    """
    Token 用量追蹤器。

    增量掃描機制：
      - 為每個 session 檔案記錄已處理到的位元組 offset
      - 每次只讀取新增的部分
      - 跨次執行持久化到 STATE_FILE
    """

    def __init__(self):
        self.state = self._load_state()
        # 記憶體快取
        self._hourly: Dict[str, HourlyBucket] = {}
        self._daily: Dict[str, DailyBucket] = {}
        self._session_calls: Dict[str, int] = {}  # session_id → call count

    # ─── 持久化 ──

    def _load_state(self) -> dict:
        os.makedirs(STATE_DIR, exist_ok=True)
        if not os.path.exists(STATE_FILE):
            return self._default_state()
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self._default_state()

    def _default_state(self) -> dict:
        return {
            "version": 1,
            "last_scan": None,
            "file_offsets": {},        # filepath → byte offset
            "daily_history": [],       # DailyBucket list (最近 30 天)
            "hourly_history": [],      # HourlyBucket list (最近 48 小時)
            "budget": {
                "daily_limit_usd": 10.0,     # 每日預算上限
                "monthly_limit_usd": 200.0,  # 每月預算上限
                "alert_thresholds": [0.7, 0.9, 1.0],  # 告警門檻百分比
                "alerts_sent": {},     # "daily:2026-02-13:0.7" → iso timestamp
            },
            "totals": {
                "all_time_tokens": 0,
                "all_time_cost_usd": 0.0,
                "all_time_calls": 0,
            },
        }

    def save_state(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)

    # ─── 增量掃描 ──

    def scan(self) -> List[APICall]:
        """
        掃描所有 session 檔案，提取新增的 API 呼叫。
        回傳新增的 APICall 列表。
        """
        if not os.path.isdir(SESSIONS_DIR):
            return []

        new_calls: List[APICall] = []
        offsets = self.state.setdefault("file_offsets", {})

        for fpath in glob.glob(os.path.join(SESSIONS_DIR, "*.jsonl")):
            prev_offset = offsets.get(fpath, 0)
            try:
                file_size = os.path.getsize(fpath)
                if file_size <= prev_offset:
                    continue  # 無新資料

                session_id = os.path.splitext(os.path.basename(fpath))[0]
                with open(fpath, "r", encoding="utf-8") as f:
                    f.seek(prev_offset)
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        call = self._extract_api_call(entry, session_id)
                        if call:
                            new_calls.append(call)

                    offsets[fpath] = f.tell()

            except Exception:
                continue

        # 清理已刪除的 session 檔案 offset
        existing = set(glob.glob(os.path.join(SESSIONS_DIR, "*.jsonl")))
        for fpath in list(offsets.keys()):
            if fpath not in existing:
                del offsets[fpath]

        self.state["last_scan"] = datetime.now(TZ_GMT8).isoformat()
        return new_calls

    def _extract_api_call(self, entry: dict, session_id: str) -> Optional[APICall]:
        """從 JSONL entry 提取 API 呼叫資訊"""
        if entry.get("type") != "message":
            return None

        msg = entry.get("message", {})
        usage = msg.get("usage")
        if not usage or usage.get("totalTokens", 0) == 0:
            return None

        # 只計算 assistant 回應（有 model 的記錄）
        model = msg.get("model", "")
        if not model or model in ("delivery-mirror",):
            return None

        # 排除零 token 的系統訊息
        total = usage.get("totalTokens", 0)
        if total <= 0:
            return None

        cost = calc_cost(model, usage)
        ts = entry.get("timestamp", msg.get("timestamp", ""))

        return APICall(
            session_id=session_id,
            message_id=entry.get("id", ""),
            timestamp=str(ts),
            model=model,
            provider=msg.get("provider", "unknown"),
            input_tokens=usage.get("input", 0),
            output_tokens=usage.get("output", 0),
            cache_read=usage.get("cacheRead", 0),
            cache_write=usage.get("cacheWrite", 0),
            total_tokens=total,
            cost_usd=cost["total"],
        )

    # ─── 聚合 ──

    def aggregate(self, calls: List[APICall]):
        """將新增的呼叫聚合到 hourly/daily bucket"""
        now = datetime.now(TZ_GMT8)
        today = now.strftime("%Y-%m-%d")

        # 載入現有 daily/hourly history
        self._load_buckets()

        for call in calls:
            # 時間解析
            try:
                if isinstance(call.timestamp, str) and "T" in call.timestamp:
                    # ISO 格式
                    ts_str = call.timestamp[:19]
                    try:
                        ts = datetime.fromisoformat(ts_str)
                    except ValueError:
                        ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    ts = ts.astimezone(TZ_GMT8)
                else:
                    # Unix timestamp (ms)
                    ts_ms = int(call.timestamp)
                    ts = datetime.fromtimestamp(ts_ms / 1000, tz=TZ_GMT8)
            except (ValueError, TypeError, OSError):
                ts = now

            date_key = ts.strftime("%Y-%m-%d")
            hour_key = ts.strftime("%Y-%m-%dT%H")

            # Hourly
            if hour_key not in self._hourly:
                self._hourly[hour_key] = HourlyBucket(hour=hour_key)
            self._hourly[hour_key].add(call)

            # Daily
            if date_key not in self._daily:
                self._daily[date_key] = DailyBucket(date=date_key)
            self._daily[date_key].add(call)

            # Session tracking
            self._session_calls[call.session_id] = self._session_calls.get(call.session_id, 0) + 1

            # Totals
            totals = self.state.setdefault("totals", {})
            totals["all_time_tokens"] = totals.get("all_time_tokens", 0) + call.total_tokens
            totals["all_time_cost_usd"] = round(totals.get("all_time_cost_usd", 0) + call.cost_usd, 6)
            totals["all_time_calls"] = totals.get("all_time_calls", 0) + 1

        # 更新 daily session count
        for sid in set(c.session_id for c in calls):
            for d_bucket in self._daily.values():
                # 簡單方式：重新計算 session 數
                pass

        self._save_buckets()

    def _load_buckets(self):
        """從 state 載入 hourly/daily buckets"""
        for h in self.state.get("hourly_history", []):
            key = h.get("hour", "")
            if key and key not in self._hourly:
                self._hourly[key] = HourlyBucket(**{k: v for k, v in h.items() if k != "hour"}, hour=key)

        for d in self.state.get("daily_history", []):
            key = d.get("date", "")
            if key and key not in self._daily:
                self._daily[key] = DailyBucket(**{
                    k: v for k, v in d.items()
                    if k not in ("date", "models", "peak_hour", "peak_hour_cost")
                }, date=key, models=d.get("models", {}),
                   peak_hour=d.get("peak_hour", ""),
                   peak_hour_cost=d.get("peak_hour_cost", 0.0))

    def _save_buckets(self):
        """將 hourly/daily buckets 寫回 state（只保留有限歷史）"""
        now = datetime.now(TZ_GMT8)

        # 只保留最近 48 小時
        cutoff_48h = (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H")
        hourly_list = sorted(
            [asdict(b) for k, b in self._hourly.items() if k >= cutoff_48h],
            key=lambda x: x["hour"]
        )
        self.state["hourly_history"] = hourly_list

        # 計算 peak_hour for each daily
        for date_key, daily in self._daily.items():
            peak_cost = 0.0
            peak_hour = ""
            for hk, hb in self._hourly.items():
                if hk.startswith(date_key) and hb.cost_usd > peak_cost:
                    peak_cost = hb.cost_usd
                    peak_hour = hk
            daily.peak_hour = peak_hour
            daily.peak_hour_cost = round(peak_cost, 6)

        # 只保留最近 30 天
        cutoff_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        daily_list = sorted(
            [asdict(b) for k, b in self._daily.items() if k >= cutoff_30d],
            key=lambda x: x["date"]
        )
        self.state["daily_history"] = daily_list

    # ─── 查詢 API ──

    def get_today_summary(self) -> dict:
        """取得今日摘要"""
        today = datetime.now(TZ_GMT8).strftime("%Y-%m-%d")
        self._load_buckets()

        bucket = self._daily.get(today)
        if not bucket:
            return {
                "date": today,
                "calls": 0, "total_tokens": 0, "cost_usd": 0.0,
                "input_tokens": 0, "output_tokens": 0,
                "cache_read": 0, "cache_write": 0,
                "models": {}, "sessions": 0,
            }

        # 計算今日 active session 數
        sessions_today = set()
        offsets = self.state.get("file_offsets", {})
        for fpath in offsets:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=TZ_GMT8)
                if mtime.strftime("%Y-%m-%d") == today:
                    sessions_today.add(os.path.basename(fpath))
            except Exception:
                continue

        return {
            "date": today,
            "calls": bucket.calls,
            "total_tokens": bucket.total_tokens,
            "input_tokens": bucket.input_tokens,
            "output_tokens": bucket.output_tokens,
            "cache_read": bucket.cache_read,
            "cache_write": bucket.cache_write,
            "cost_usd": round(bucket.cost_usd, 4),
            "models": bucket.models,
            "sessions": len(sessions_today),
            "peak_hour": bucket.peak_hour,
            "peak_hour_cost": round(bucket.peak_hour_cost, 4),
        }

    def get_daily_history(self, days: int = 7) -> List[dict]:
        """取得最近 N 天的每日摘要"""
        self._load_buckets()
        now = datetime.now(TZ_GMT8)
        cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        result = []
        for d in sorted(self._daily.values(), key=lambda x: x.date):
            if d.date >= cutoff:
                result.append(asdict(d))
        return result

    def get_hourly_history(self, hours: int = 24) -> List[dict]:
        """取得最近 N 小時的每小時摘要"""
        self._load_buckets()
        now = datetime.now(TZ_GMT8)
        cutoff = (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H")
        result = []
        for h in sorted(self._hourly.values(), key=lambda x: x.hour):
            if h.hour >= cutoff:
                result.append(asdict(h))
        return result

    def get_monthly_summary(self) -> dict:
        """取得當月摘要"""
        self._load_buckets()
        now = datetime.now(TZ_GMT8)
        month_prefix = now.strftime("%Y-%m")

        total_tokens = 0
        total_cost = 0.0
        total_calls = 0
        days_active = 0

        for d in self._daily.values():
            if d.date.startswith(month_prefix):
                total_tokens += d.total_tokens
                total_cost += d.cost_usd
                total_calls += d.calls
                if d.calls > 0:
                    days_active += 1

        return {
            "month": month_prefix,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "total_calls": total_calls,
            "days_active": days_active,
            "avg_daily_cost": round(total_cost / max(days_active, 1), 4),
        }

    def get_model_breakdown(self, days: int = 7) -> Dict[str, dict]:
        """取得模型用量分佈"""
        self._load_buckets()
        now = datetime.now(TZ_GMT8)
        cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        models: Dict[str, dict] = {}

        for d in self._daily.values():
            if d.date < cutoff:
                continue
            for model, count in d.models.items():
                if model not in models:
                    models[model] = {"calls": 0, "proportion": 0.0}
                models[model]["calls"] += count

        total = sum(m["calls"] for m in models.values())
        for m in models.values():
            m["proportion"] = round(m["calls"] / max(total, 1) * 100, 1)

        return models

    def get_cache_efficiency(self, days: int = 7) -> dict:
        """計算快取效率"""
        self._load_buckets()
        now = datetime.now(TZ_GMT8)
        cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")

        total_input = 0
        total_cache_read = 0
        total_cache_write = 0

        for d in self._daily.values():
            if d.date >= cutoff:
                total_input += d.input_tokens
                total_cache_read += d.cache_read
                total_cache_write += d.cache_write

        # Cache hit rate = cacheRead / (cacheRead + input)
        total_prompt = total_input + total_cache_read
        hit_rate = (total_cache_read / max(total_prompt, 1)) * 100

        # 快取節省 = cacheRead * (input_price - cache_price) / 1M
        p = get_pricing("deepseek-chat")
        savings = (total_cache_read / 1_000_000) * (p["input"] - p["cache_read"])

        return {
            "total_prompt_tokens": total_prompt,
            "cache_hit_tokens": total_cache_read,
            "cache_miss_tokens": total_input,
            "cache_write_tokens": total_cache_write,
            "hit_rate_pct": round(hit_rate, 1),
            "cost_savings_usd": round(savings, 4),
        }

    # ─── 預算檢查 ──

    def check_budget(self) -> List[dict]:
        """
        檢查今日/本月是否超過預算門檻。
        回傳需要告警的事件列表。
        """
        budget = self.state.get("budget", {})
        daily_limit = budget.get("daily_limit_usd", 10.0)
        monthly_limit = budget.get("monthly_limit_usd", 200.0)
        thresholds = budget.get("alert_thresholds", [0.7, 0.9, 1.0])
        alerts_sent = budget.setdefault("alerts_sent", {})

        events = []
        today = datetime.now(TZ_GMT8).strftime("%Y-%m-%d")

        # 今日檢查
        today_summary = self.get_today_summary()
        today_cost = today_summary["cost_usd"]

        for pct in thresholds:
            limit_at_pct = daily_limit * pct
            alert_key = f"daily:{today}:{pct}"
            if today_cost >= limit_at_pct and alert_key not in alerts_sent:
                events.append({
                    "type": "daily_budget",
                    "threshold_pct": pct,
                    "current_cost": today_cost,
                    "limit": daily_limit,
                    "usage_pct": round(today_cost / max(daily_limit, 0.001) * 100, 1),
                })
                alerts_sent[alert_key] = datetime.now(TZ_GMT8).isoformat()

        # 月度檢查
        monthly = self.get_monthly_summary()
        month_cost = monthly["total_cost_usd"]
        month_key = monthly["month"]

        for pct in thresholds:
            limit_at_pct = monthly_limit * pct
            alert_key = f"monthly:{month_key}:{pct}"
            if month_cost >= limit_at_pct and alert_key not in alerts_sent:
                events.append({
                    "type": "monthly_budget",
                    "threshold_pct": pct,
                    "current_cost": month_cost,
                    "limit": monthly_limit,
                    "usage_pct": round(month_cost / max(monthly_limit, 0.001) * 100, 1),
                })
                alerts_sent[alert_key] = datetime.now(TZ_GMT8).isoformat()

        # 清理超過 35 天的 alert_sent 記錄
        cutoff = (datetime.now(TZ_GMT8) - timedelta(days=35)).isoformat()
        for key in list(alerts_sent.keys()):
            if alerts_sent[key] < cutoff:
                del alerts_sent[key]

        return events

    def update_budget(self, daily_limit: float = None, monthly_limit: float = None):
        """更新預算設定"""
        budget = self.state.setdefault("budget", {})
        if daily_limit is not None:
            budget["daily_limit_usd"] = daily_limit
        if monthly_limit is not None:
            budget["monthly_limit_usd"] = monthly_limit

    def get_budget(self) -> dict:
        """取得預算設定與當前使用"""
        budget = self.state.get("budget", {})
        today = self.get_today_summary()
        monthly = self.get_monthly_summary()

        daily_limit = budget.get("daily_limit_usd", 10.0)
        monthly_limit = budget.get("monthly_limit_usd", 200.0)

        return {
            "daily_limit_usd": daily_limit,
            "monthly_limit_usd": monthly_limit,
            "today_cost_usd": today["cost_usd"],
            "today_pct": round(today["cost_usd"] / max(daily_limit, 0.001) * 100, 1),
            "month_cost_usd": monthly["total_cost_usd"],
            "month_pct": round(monthly["total_cost_usd"] / max(monthly_limit, 0.001) * 100, 1),
        }

    # ─── 趨勢分析 ──

    def get_trend(self, days: int = 7) -> dict:
        """分析費用趨勢"""
        history = self.get_daily_history(days)
        if len(history) < 2:
            return {"trend": "insufficient_data", "change_pct": 0.0, "direction": "flat"}

        costs = [d["cost_usd"] for d in history]
        avg = sum(costs) / len(costs)
        latest = costs[-1]

        if avg <= 0:
            return {"trend": "flat", "change_pct": 0.0, "direction": "flat"}

        change_pct = ((latest - avg) / avg) * 100

        if change_pct > 20:
            direction = "up_significant"
        elif change_pct > 5:
            direction = "up"
        elif change_pct < -20:
            direction = "down_significant"
        elif change_pct < -5:
            direction = "down"
        else:
            direction = "flat"

        return {
            "trend": direction,
            "change_pct": round(change_pct, 1),
            "direction": direction,
            "avg_daily": round(avg, 4),
            "latest_daily": round(latest, 4),
        }

    # ─── 完整掃描+聚合 ──

    def refresh(self) -> dict:
        """
        完整掃描 + 聚合 + 儲存。
        回傳今日摘要。
        """
        calls = self.scan()
        if calls:
            self.aggregate(calls)
        
        # 更新預算狀態
        self._update_budget_status()
        
        self.save_state()
        return self.get_today_summary()
    
    def _update_budget_status(self):
        """更新預算狀態中的成本和使用率"""
        today = self.get_today_summary()
        monthly = self.get_monthly_summary()
        budget = self.state.get("budget", {})
        
        daily_limit = budget.get("daily_limit_usd", 10.0)
        monthly_limit = budget.get("monthly_limit_usd", 200.0)
        
        # 確保 budget_status 存在
        if "budget_status" not in self.state:
            self.state["budget_status"] = {}
        
        self.state["budget_status"].update({
            "daily_limit_usd": daily_limit,
            "monthly_limit_usd": monthly_limit,
            "today_cost": today["cost_usd"],
            "month_cost": monthly["total_cost_usd"],
            "daily_percent": round(today["cost_usd"] / max(daily_limit, 0.001) * 100, 1),
            "monthly_percent": round(monthly["total_cost_usd"] / max(monthly_limit, 0.001) * 100, 1),
        })


# ─── CLI 入口 ────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    tracker = TokenTracker()
    summary = tracker.refresh()

    print(f"📊 Token Tracker — {summary['date']}")
    print(f"   呼叫次數: {summary['calls']}")
    print(f"   總 Token: {summary['total_tokens']:,}")
    print(f"   費用: ${summary['cost_usd']:.4f}")
    print(f"   快取命中: {summary['cache_read']:,}")
    print(f"   工作階段: {summary['sessions']}")
    if summary.get("models"):
        print(f"   模型分佈: {summary['models']}")

    # 預算檢查
    budget_alerts = tracker.check_budget()
    if budget_alerts:
        print(f"\n⚠️ 預算告警:")
        for a in budget_alerts:
            print(f"   {a['type']}: ${a['current_cost']:.4f} / ${a['limit']:.2f} ({a['usage_pct']}%)")

    tracker.save_state()
