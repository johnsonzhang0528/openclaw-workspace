#!/usr/bin/env python3
"""
Token 成本治理引擎 (Token Governance)
═════════════════════════════════════
職責：
  1. 排程驅動：每次 health_engine 執行時增量掃描 token 用量
  2. 預算告警：超過 70%/90%/100% 時 Telegram 通知
  3. Telegram 報告：今日/本週/本月成本報告（HTML 格式）
  4. 優化建議：基於快取效率、趨勢分析給出可行動建議
  5. 整合 usage_cost_report.py 的每日報告（可選取代）

此模組不自行排程，由 health_engine.py 在每 30 秒週期中呼叫。
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from token_tracker import TokenTracker, get_pricing

TZ_GMT8 = timezone(timedelta(hours=8))

# ─── 報告格式化 ──────────────────────────────────────────

def _bar(pct: float, width: int = 10) -> str:
    """生成文字進度條"""
    filled = min(width, max(0, int(pct / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def _cost_icon(pct: float) -> str:
    """根據預算百分比回傳圖標"""
    if pct >= 100:
        return "🔴"
    elif pct >= 90:
        return "🟠"
    elif pct >= 70:
        return "🟡"
    return "🟢"


def _trend_icon(direction: str) -> str:
    """趨勢圖標"""
    icons = {
        "up_significant": "📈🔴",
        "up": "📈",
        "flat": "📊",
        "down": "📉",
        "down_significant": "📉🟢",
        "insufficient_data": "📊",
    }
    return icons.get(direction, "📊")


def _fmt_tokens(n: int) -> str:
    """格式化 token 數量"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ─── 報告產生器 ──────────────────────────────────────────

def generate_token_summary(tracker: TokenTracker = None) -> str:
    """
    💰 Token 成本摘要（供 Telegram 選單使用）
    精簡版，用於主控面板的「Token 成本」子選單。
    """
    if tracker is None:
        tracker = TokenTracker()
        tracker.refresh()

    today = tracker.get_today_summary()
    budget = tracker.get_budget()
    trend = tracker.get_trend(7)
    cache = tracker.get_cache_efficiency(7)
    monthly = tracker.get_monthly_summary()

    lines = [
        "<b>💰 Token 成本摘要</b>",
        f"{'━' * 25}",
        "",
        "<b>📅 今日</b>",
        f"  呼叫: <b>{today['calls']}</b> 次",
        f"  Token: <code>{_fmt_tokens(today['total_tokens'])}</code>"
        f" (入 {_fmt_tokens(today['input_tokens'])} / 出 {_fmt_tokens(today['output_tokens'])})",
        f"  費用: <b>${today['cost_usd']:.4f}</b>",
        f"  {_cost_icon(budget['today_pct'])} 預算: <code>{_bar(budget['today_pct'])}</code>"
        f" {budget['today_pct']:.0f}% (${budget['daily_limit_usd']:.2f})",
    ]

    if today.get("peak_hour"):
        pk = today["peak_hour"][-2:]  # 取 HH
        lines.append(f"  ⏰ 尖峰: {pk}:00 (${today.get('peak_hour_cost', 0):.4f})")

    lines.extend([
        "",
        "<b>📆 本月</b>",
        f"  費用: <b>${monthly['total_cost_usd']:.4f}</b>",
        f"  {_cost_icon(budget['month_pct'])} 預算: <code>{_bar(budget['month_pct'])}</code>"
        f" {budget['month_pct']:.0f}% (${budget['monthly_limit_usd']:.2f})",
        f"  活躍天數: {monthly['days_active']} | 日均: ${monthly['avg_daily_cost']:.4f}",
        "",
        f"<b>📈 趨勢 (7日)</b>",
        f"  {_trend_icon(trend['direction'])} {_trend_text(trend)}",
        "",
        f"<b>💾 快取效率 (7日)</b>",
        f"  命中率: <b>{cache['hit_rate_pct']:.1f}%</b>",
        f"  節省: <b>${cache['cost_savings_usd']:.4f}</b>",
    ])

    return "\n".join(lines)


def generate_token_detail(tracker: TokenTracker = None) -> str:
    """
    📊 Token 費用詳情（7 日歷史 + 模型分佈 + 優化建議）
    """
    if tracker is None:
        tracker = TokenTracker()
        tracker.refresh()

    history = tracker.get_daily_history(7)
    models = tracker.get_model_breakdown(7)
    cache = tracker.get_cache_efficiency(7)
    trend = tracker.get_trend(7)
    budget = tracker.get_budget()

    lines = [
        "<b>📊 Token 費用詳情</b>",
        f"{'━' * 25}",
    ]

    # 7 日歷史
    lines.append("\n<b>📅 近 7 日費用</b>")
    if history:
        max_cost = max(d.get("cost_usd", 0) for d in history) or 1
        for d in history:
            date = d["date"][5:]  # MM-DD
            cost = d.get("cost_usd", 0)
            tokens = d.get("total_tokens", 0)
            calls = d.get("calls", 0)
            bar_len = min(12, max(1, int(cost / max_cost * 12))) if cost > 0 else 0
            bar = "█" * bar_len + "░" * (12 - bar_len)
            lines.append(
                f"  <code>{date}</code> <code>{bar}</code>"
                f" ${cost:.4f} ({_fmt_tokens(tokens)}, {calls}次)"
            )
    else:
        lines.append("  尚無資料")

    # 模型分佈
    lines.append("\n<b>🤖 模型使用 (7日)</b>")
    if models:
        for model, info in sorted(models.items(), key=lambda x: -x[1]["calls"]):
            lines.append(f"  {model}: <b>{info['calls']}</b> 次 ({info['proportion']}%)")
    else:
        lines.append("  尚無資料")

    # 快取效率
    lines.append("\n<b>💾 快取分析</b>")
    lines.append(f"  總 Prompt: {_fmt_tokens(cache['total_prompt_tokens'])}")
    lines.append(f"  命中: {_fmt_tokens(cache['cache_hit_tokens'])} ({cache['hit_rate_pct']:.1f}%)")
    lines.append(f"  未命中: {_fmt_tokens(cache['cache_miss_tokens'])}")
    lines.append(f"  節省金額: <b>${cache['cost_savings_usd']:.4f}</b>")

    # 預算狀態
    lines.append("\n<b>💳 預算</b>")
    lines.append(
        f"  日額: {_cost_icon(budget['today_pct'])} "
        f"${budget['today_cost_usd']:.4f} / ${budget['daily_limit_usd']:.2f}"
        f" ({budget['today_pct']:.0f}%)"
    )
    lines.append(
        f"  月額: {_cost_icon(budget['month_pct'])} "
        f"${budget['month_cost_usd']:.4f} / ${budget['monthly_limit_usd']:.2f}"
        f" ({budget['month_pct']:.0f}%)"
    )

    # 優化建議
    suggestions = _generate_suggestions(trend, cache, budget)
    if suggestions:
        lines.append("\n<b>💡 優化建議</b>")
        for s in suggestions:
            lines.append(f"  • {s}")

    return "\n".join(lines)


def generate_token_hourly(tracker: TokenTracker = None) -> str:
    """⏰ 最近 24 小時用量分佈"""
    if tracker is None:
        tracker = TokenTracker()
        tracker.refresh()

    hourly = tracker.get_hourly_history(24)

    lines = [
        "<b>⏰ 24 小時用量分佈</b>",
        f"{'━' * 25}",
    ]

    if not hourly:
        lines.append("\n尚無資料")
        return "\n".join(lines)

    max_cost = max(h.get("cost_usd", 0) for h in hourly) or 1
    for h in hourly:
        hr = h["hour"][-2:]  # 取 HH (已包含 GMT+8 的小時)
        cost = h.get("cost_usd", 0)
        calls = h.get("calls", 0)
        tokens = h.get("total_tokens", 0)
        bar_len = min(10, max(0, int(cost / max_cost * 10))) if cost > 0 else 0
        bar = "█" * bar_len + "░" * (10 - bar_len)
        lines.append(
            f"  <code>{hr}:00</code> <code>{bar}</code>"
            f" ${cost:.4f} ({calls}×, {_fmt_tokens(tokens)})"
        )

    return "\n".join(lines)


def generate_budget_status(tracker: TokenTracker = None) -> str:
    """💳 預算狀態"""
    if tracker is None:
        tracker = TokenTracker()
        tracker.refresh()

    budget = tracker.get_budget()
    monthly = tracker.get_monthly_summary()
    now = datetime.now(TZ_GMT8)

    lines = [
        "<b>💳 預算狀態</b>",
        f"{'━' * 25}",
        "",
        "<b>📅 今日</b>",
        f"  {_cost_icon(budget['today_pct'])} "
        f"<code>{_bar(budget['today_pct'], 15)}</code>",
        f"  已用: <b>${budget['today_cost_usd']:.4f}</b> / ${budget['daily_limit_usd']:.2f}",
        f"  使用率: <b>{budget['today_pct']:.1f}%</b>",
        f"  剩餘: ${max(0, budget['daily_limit_usd'] - budget['today_cost_usd']):.4f}",
        "",
        "<b>📆 本月 ({month})</b>".format(month=monthly['month']),
        f"  {_cost_icon(budget['month_pct'])} "
        f"<code>{_bar(budget['month_pct'], 15)}</code>",
        f"  已用: <b>${budget['month_cost_usd']:.4f}</b> / ${budget['monthly_limit_usd']:.2f}",
        f"  使用率: <b>{budget['month_pct']:.1f}%</b>",
        f"  剩餘: ${max(0, budget['monthly_limit_usd'] - budget['month_cost_usd']):.4f}",
    ]

    # 預估月底花費
    days_in_month = 30  # 簡化
    day_of_month = now.day
    if monthly["days_active"] > 0 and day_of_month > 0:
        projected = (monthly["total_cost_usd"] / day_of_month) * days_in_month
        lines.append(f"\n<b>📈 月底預估</b>")
        lines.append(f"  預估: <b>${projected:.2f}</b>")
        proj_pct = (projected / max(budget['monthly_limit_usd'], 0.001)) * 100
        lines.append(f"  預估使用率: {_cost_icon(proj_pct)} {proj_pct:.0f}%")

    # 告警門檻
    lines.append(f"\n<b>🔔 告警門檻</b>")
    lines.append(f"  日額 70%: ${budget['daily_limit_usd'] * 0.7:.2f}")
    lines.append(f"  日額 90%: ${budget['daily_limit_usd'] * 0.9:.2f}")
    lines.append(f"  月額 70%: ${budget['monthly_limit_usd'] * 0.7:.2f}")
    lines.append(f"  月額 90%: ${budget['monthly_limit_usd'] * 0.9:.2f}")

    lines.append(f"\n<code>{now.strftime('%Y-%m-%d %H:%M:%S')} GMT+8</code>")

    return "\n".join(lines)


# ─── 優化建議 ────────────────────────────────────────────

def _generate_suggestions(trend: dict, cache: dict, budget: dict) -> List[str]:
    """基於當前數據生成可行動的優化建議"""
    suggestions = []

    # 快取效率
    hit_rate = cache.get("hit_rate_pct", 0)
    if hit_rate < 30:
        suggestions.append(
            f"快取命中率偏低 ({hit_rate:.0f}%)，考慮合併相似查詢或啟用 prompt caching"
        )
    elif hit_rate > 80:
        suggestions.append(
            f"✅ 快取命中率良好 ({hit_rate:.0f}%)，持續維持"
        )

    # 趨勢
    change = trend.get("change_pct", 0)
    if change > 30:
        suggestions.append(
            f"費用明顯上升 (+{change:.0f}%)，建議檢查是否有異常大量呼叫"
        )
    elif change < -20:
        suggestions.append(
            f"費用持續下降 ({change:.0f}%)，優化策略有效 ✅"
        )

    # 預算
    if budget.get("today_pct", 0) > 80:
        suggestions.append(
            "今日預算接近上限，建議減少非必要呼叫或提高日額"
        )
    if budget.get("month_pct", 0) > 70:
        suggestions.append(
            "本月預算使用超過 70%，留意剩餘額度"
        )

    if not suggestions:
        suggestions.append("目前用量正常，無特別優化建議")

    return suggestions


def _trend_text(trend: dict) -> str:
    """將趨勢轉為可讀文字"""
    direction = trend.get("direction", "flat")
    change = trend.get("change_pct", 0)
    avg = trend.get("avg_daily", 0)

    texts = {
        "up_significant": f"大幅上升 +{change:.0f}% (7日均 ${avg:.4f})",
        "up": f"略微上升 +{change:.0f}% (7日均 ${avg:.4f})",
        "flat": f"持平 ({change:+.0f}%, 7日均 ${avg:.4f})",
        "down": f"略微下降 {change:.0f}% (7日均 ${avg:.4f})",
        "down_significant": f"大幅下降 {change:.0f}% (7日均 ${avg:.4f})",
        "insufficient_data": "數據不足，尚無趨勢分析",
    }
    return texts.get(direction, f"變化 {change:+.0f}%")


# ─── 預算告警格式化 ──────────────────────────────────────

def format_budget_alert(event: dict) -> str:
    """將預算告警事件格式化為 Telegram HTML 訊息"""
    alert_type = event.get("type", "budget")
    pct = event.get("threshold_pct", 1.0) * 100
    usage_pct = event.get("usage_pct", 0)
    current = event.get("current_cost", 0)
    limit = event.get("limit", 0)

    if pct >= 100:
        icon = "🚨"
        severity = "超出上限"
    elif pct >= 90:
        icon = "⚠️"
        severity = "接近上限"
    else:
        icon = "💡"
        severity = "預警提醒"

    scope = "每日" if alert_type == "daily_budget" else "每月"
    now = datetime.now(TZ_GMT8).strftime("%Y-%m-%d %H:%M:%S")

    return (
        f"{icon} <b>Token 成本{severity}</b>\n"
        f"{'━' * 25}\n\n"
        f"📋 類型: {scope}預算\n"
        f"💰 當前: <b>${current:.4f}</b> / ${limit:.2f}\n"
        f"📊 使用率: <b>{usage_pct:.1f}%</b> (門檻 {pct:.0f}%)\n"
        f"{'━' * 25}\n"
        f"<code>{now} GMT+8</code>"
    )


# ─── 健康引擎整合入口 ──────────────────────────────────

def run_token_check(sender=None) -> Tuple[List[dict], dict]:
    """
    供 health_engine.py 在每次執行週期呼叫。

    回傳：
      - budget_alerts: 需要發送的預算告警事件列表
      - today_summary: 今日摘要 dict

    若 sender 不為 None，會自動發送預算告警。
    預算告警在 check_budget() 中標記為已發送（寫入 alerts_sent）。
    若 Telegram 發送失敗，回滾 alerts_sent 以便下次重試。
    """
    tracker = TokenTracker()
    summary = tracker.refresh()
    budget_alerts = tracker.check_budget()

    if sender and budget_alerts:
        failed_keys = []
        for event in budget_alerts:
            text = format_budget_alert(event)
            pct = event.get("threshold_pct", 1.0)
            a_type = event.get("type", "budget")
            today = datetime.now(TZ_GMT8).strftime("%Y-%m-%d")
            month = datetime.now(TZ_GMT8).strftime("%Y-%m")
            scope_key = today if a_type == "daily_budget" else month
            alert_key = f"{a_type.replace('_budget', '')}:{scope_key}:{pct}"
            try:
                sender.send(text)
            except Exception as e:
                print(f"⚠️ Token 預算告警發送失敗: {e}")
                failed_keys.append(alert_key)

        # 回滾失敗的告警標記，讓下次週期可以重試
        if failed_keys:
            alerts_sent = tracker.state.get("budget", {}).get("alerts_sent", {})
            for key in failed_keys:
                alerts_sent.pop(key, None)

    tracker.save_state()
    return budget_alerts, summary
