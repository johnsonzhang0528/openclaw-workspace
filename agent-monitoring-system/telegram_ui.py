#!/usr/bin/env python3
"""
Telegram UI 元件庫
═══════════════════
職責：
  1. 主控面板選單定義（IA、鍵盤佈局）
  2. callback_data 編碼/解碼（64-byte 限制安全）
  3. 頁面內容產生器
  4. Bot 指令註冊清單

callback_data 格式：
  m:{page}
  m:{page}:{action}
  m:{page}:{action}:{arg}

  page   = home | mon | sys | bak | cfg | log | info
  action = 因頁面而異
  arg    = 可選參數

選單 IA（資訊架構）：
  /menu → 主面板
  ├── 📊 監控中心 (mon)
  │   ├── 📋 健康儀表板 (mon:dash)
  │   ├── 📈 效能詳情   (mon:perf)
  │   └── ⚠️ 最近告警   (mon:alerts)
  ├── 🔧 系統操作 (sys)     [admin+]
  │   ├── 🔄 重啟 Gateway (sys:restart / sys:restart:y)
  │   ├── 📋 最近日誌     (sys:logs)
  │   └── 🩺 健康檢查     (sys:health)
  ├── 💾 備份管理 (bak)     [admin+]
  │   ├── 📦 立即備份     (bak:now)
  │   ├── ✅ 驗證備份     (bak:verify)
  │   ├── 📋 備份列表     (bak:list)
  │   └── 📊 備份狀態     (bak:status)
  ├── ⚙️ 設定管理 (cfg)     [member+]
  │   ├── 📋 查看設定     (cfg:view)
  │   └── 📜 變更紀錄     (cfg:history)
  ├── � Token 成本 (tok)
  │   ├── 💰 成本摘要     (tok:summary)
  │   ├── 📊 費用詳情     (tok:detail)
  │   ├── ⏰ 24h 分佈     (tok:hourly)
  │   └── 💳 預算狀態     (tok:budget)
  ├── �📝 日誌報告 (log)
  │   └── 📊 磁碟使用報告 (log:disk)
  └── ℹ️ 系統資訊 (info)
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

TZ_GMT8 = timezone(timedelta(hours=8))

# ─── Bot 指令（setMyCommands）────────────────────────
#
# 所有指令定義統一在 command_registry.py（唯一來源）。
# 此處僅匯入，不重複定義。詳見 command_registry.py 的說明。

from command_registry import MONITOR_COMMANDS as BOT_COMMANDS


# ─── Callback Data 編碼/解碼 ─────────────────────────────

def cb(*parts: str) -> str:
    """
    構建 callback_data 字串。

    用法：
        cb("home")              → "m:home"
        cb("mon", "dash")       → "m:mon:dash"
        cb("sys", "restart", "y") → "m:sys:restart:y"

    所有生成的字串均以 "m:" 開頭，用於與舊版 alert button 區分。
    """
    return ":".join(["m"] + list(parts))


def parse_cb(data: str) -> Tuple[str, str, str]:
    """
    解析 callback_data → (page, action, arg)。

    如果不是 menu callback（不以 "m:" 開頭），回傳 ("", "", "")。
    """
    parts = data.split(":")
    if not parts or parts[0] != "m":
        return "", "", ""
    page = parts[1] if len(parts) > 1 else ""
    action = parts[2] if len(parts) > 2 else ""
    arg = ":".join(parts[3:]) if len(parts) > 3 else ""
    return page, action, arg


# ─── 鍵盤佈局 ────────────────────────────────────────────

def _btn(text: str, data: str) -> dict:
    """建立 inline keyboard button"""
    return {"text": text, "callback_data": data}


def kb_main_menu() -> list:
    """主選單鍵盤 — 每個按鈕對應一個 slash command，確保 Gateway AI 路徑也能正確處理"""
    return [
        [_btn("📊 監控儀表板", "/monitor"),  _btn("📋 開發日報", "/devreport")],
        [_btn("💰 費用報告", "/costreport"), _btn("📜 Git 紀錄", "/gitlog")],
        [_btn("💾 快速備份", "/quickbackup"), _btn("ℹ️ 系統資訊", "/info")],
    ]


def kb_monitor() -> list:
    """監控中心子選單"""
    return [
        [_btn("📋 健康儀表板", cb("mon", "dash"))],
        [_btn("📈 效能詳情", cb("mon", "perf")), _btn("⚠️ 最近告警", cb("mon", "alerts"))],
        [_btn("🔙 返回主選單", cb("home"))],
    ]


def kb_system() -> list:
    """系統操作子選單"""
    return [
        [_btn("🔄 重啟 Gateway", cb("sys", "restart"))],
        [_btn("📋 最近日誌", cb("sys", "logs")), _btn("🩺 健康檢查", cb("sys", "health"))],
        [_btn("🔙 返回主選單", cb("home"))],
    ]


def kb_backup() -> list:
    """備份管理子選單"""
    return [
        [_btn("📦 立即備份", cb("bak", "now")), _btn("✅ 驗證備份", cb("bak", "verify"))],
        [_btn("📋 備份列表", cb("bak", "list")), _btn("📊 備份狀態", cb("bak", "status"))],
        [_btn("🔙 返回主選單", cb("home"))],
    ]


def kb_config() -> list:
    """設定管理子選單"""
    return [
        [_btn("📋 查看設定", cb("cfg", "view")), _btn("📜 變更紀錄", cb("cfg", "history"))],
        [_btn("🔙 返回主選單", cb("home"))],
    ]


def kb_logs() -> list:
    """日誌報告子選單"""
    return [
        [_btn("📊 磁碟使用報告", cb("log", "disk"))],
        [_btn("🔙 返回主選單", cb("home"))],
    ]


def kb_token() -> list:
    """Token 成本子選單"""
    return [
        [_btn("💰 成本摘要", cb("tok", "summary")), _btn("📊 費用詳情", cb("tok", "detail"))],
        [_btn("⏰ 24h 分佈", cb("tok", "hourly")), _btn("💳 預算狀態", cb("tok", "budget"))],
        [_btn("🔙 返回主選單", cb("home"))],
    ]


def kb_back() -> list:
    """純返回按鈕（用於詳情頁面）"""
    return [[_btn("🔙 返回主選單", cb("home"))]]


def kb_confirm_restart() -> list:
    """重啟確認鍵盤"""
    return [
        [_btn("✅ 確認重啟", cb("sys", "restart", "y")), _btn("❌ 取消", cb("sys"))],
    ]


# ─── 訊息安全 ────────────────────────────────────────────

MAX_MSG_LEN = 4000  # Telegram 限制 4096，留邊際


def truncate(text: str, max_len: int = MAX_MSG_LEN) -> str:
    """截斷訊息至 Telegram 安全長度"""
    if len(text) <= max_len:
        return text
    return text[:max_len - 30] + "\n\n<i>...內容已截斷</i>"


def _escape_html(text: str) -> str:
    """HTML entity 跳脫"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─── 靜態頁面內容 ────────────────────────────────────────

def page_home(score: int = 0, grade: str = "?", ts: str = "", compact: bool = False) -> str:
    """主選單頁面。compact=True 時省略健康分數（/reset 時 Dashboard 已顯示）"""
    if compact:
        return (
            f"<b>📱 主控面板</b>\n"
            f"{'━' * 25}\n"
            f"選擇要執行的操作："
        )
    ge = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "💀"}.get(grade, "❓")
    return (
        f"<b>📱 主控面板</b>\n"
        f"{'━' * 25}\n"
        f"{ge} <b>健康分數: {score}/100 ({grade})</b>\n"
        f"<code>更新: {ts or '?'}</code>\n\n"
        f"選擇功能："
    )


def page_monitor_menu(score: int = 0, grade: str = "?") -> str:
    """監控中心子選單頁面"""
    ge = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "💀"}.get(grade, "❓")
    return (
        f"<b>📊 監控中心</b>\n"
        f"{'━' * 25}\n"
        f"{ge} 健康分數: {score}/100 ({grade})\n\n"
        f"選擇子功能："
    )


def page_system_menu(gw_running: bool = True) -> str:
    """系統操作子選單頁面"""
    icon = "🟢 運行中" if gw_running else "🔴 已停止"
    return (
        f"<b>🔧 系統操作</b>\n"
        f"{'━' * 25}\n"
        f"Gateway: {icon}\n\n"
        f"選擇操作："
    )


def page_backup_menu() -> str:
    """備份管理子選單頁面"""
    return (
        f"<b>💾 備份管理</b>\n"
        f"{'━' * 25}\n\n"
        f"選擇操作："
    )


def page_config_menu() -> str:
    """設定管理子選單頁面"""
    return (
        f"<b>⚙️ 設定管理</b>\n"
        f"{'━' * 25}\n\n"
        f"選擇操作："
    )


def page_logs_menu() -> str:
    """日誌報告子選單頁面"""
    return (
        f"<b>📝 日誌報告</b>\n"
        f"{'━' * 25}\n\n"
        f"選擇操作："
    )


def page_token_menu() -> str:
    """Token 成本子選單頁面"""
    return (
        f"<b>💰 Token 成本管理</b>\n"
        f"{'━' * 25}\n\n"
        f"選擇操作："
    )


def page_confirm_restart() -> str:
    """重啟確認頁面"""
    return (
        f"<b>⚠️ 確認重啟 Gateway</b>\n"
        f"{'━' * 25}\n\n"
        f"這將會重啟 OpenClaw Gateway 服務。\n"
        f"重啟期間（約 1 分鐘）所有請求將無法處理。\n\n"
        f"確定要繼續嗎？"
    )


def page_help() -> str:
    """指令說明頁面"""
    return (
        f"<b>❓ 指令說明</b>\n"
        f"{'━' * 25}\n\n"
        f"<b>指令列表：</b>\n"
        f"  /menu — 開啟主控面板\n"
        f"  /monitor — 查看監控儀表板\n"
        f"  /token — Token 成本摘要\n"
        f"  /backup — 備份狀態\n"
        f"  /config — 查看當前設定\n"
        f"  /logs — 磁碟使用報告\n"
        f"  /info — 系統資訊\n"
        f"  /help — 顯示此說明\n\n"
        f"<b>快捷操作：</b>\n"
        f"點擊主控面板中的按鈕即可操作\n"
        f"無需記憶任何指令 ✨\n\n"
        f"<b>權限層級：</b>\n"
        f"  👁️ viewer — 檢視監控\n"
        f"  👤 member — 查看設定/報告/成本\n"
        f"  🛡️ admin — 重啟/備份/變更設定\n"
        f"  👑 owner — 管理租戶與角色"
    )


# ─── 動態內容產生器 ──────────────────────────────────────
# 以下函式會讀取系統狀態或執行指令來產生內容。
# 全部回傳 HTML 格式字串，已截斷至安全長度。

def generate_perf_detail() -> str:
    """效能詳情：CPU、記憶體、磁碟、負載、Top 行程"""
    lines = [f"<b>📈 效能詳情</b>", f"{'━' * 25}"]

    # CPU
    try:
        cpu_count = os.cpu_count() or 1
        load1, load5, load15 = os.getloadavg()
        lines.append(f"\n<b>CPU</b> ({cpu_count} 核心)")
        lines.append(f"  負載: {load1:.2f} / {load5:.2f} / {load15:.2f}")
    except Exception:
        pass

    # Memory
    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = int(parts[1].strip().split()[0])  # kB
                    meminfo[key] = val
        total = meminfo.get("MemTotal", 0) // 1024
        avail = meminfo.get("MemAvailable", 0) // 1024
        used = total - avail
        pct = (used / total * 100) if total > 0 else 0
        lines.append(f"\n<b>RAM</b>")
        lines.append(f"  使用: {used}/{total} MB ({pct:.1f}%)")
        lines.append(f"  可用: {avail} MB")
    except Exception:
        pass

    # Disk
    try:
        st = os.statvfs("/")
        total_gb = st.f_frsize * st.f_blocks / (1024**3)
        free_gb = st.f_frsize * st.f_bfree / (1024**3)
        used_gb = total_gb - free_gb
        pct = (used_gb / total_gb * 100) if total_gb > 0 else 0
        lines.append(f"\n<b>Disk</b>")
        lines.append(f"  使用: {used_gb:.1f}/{total_gb:.1f} GB ({pct:.1f}%)")
        lines.append(f"  可用: {free_gb:.1f} GB")
    except Exception:
        pass

    # Top 5 processes
    try:
        out = subprocess.check_output(
            ["ps", "aux", "--sort=-%cpu"], text=True, timeout=5
        ).strip().split("\n")
        if len(out) > 1:
            lines.append(f"\n<b>Top 5 行程 (CPU)</b>")
            for row in out[1:6]:
                cols = row.split(None, 10)
                if len(cols) >= 11:
                    cpu_pct = cols[2]
                    mem_pct = cols[3]
                    cmd = cols[10][:35]
                    lines.append(f"  <code>{cpu_pct:>5}% {mem_pct:>5}% {_escape_html(cmd)}</code>")
    except Exception:
        pass

    return truncate("\n".join(lines))


def generate_recent_alerts(state: dict) -> str:
    """最近告警列表"""
    lines = [f"<b>⚠️ 最近告警</b>", f"{'━' * 25}"]

    active = state.get("alerts", {}).get("active_alerts", [])
    if not active:
        lines.append("\n✅ 目前沒有活躍告警")
    else:
        lines.append(f"\n共 {len(active)} 項活躍告警：\n")
        for a in active[-10:]:
            sev = "🚨" if a.get("severity") == "critical" else "⚠️"
            ts = a.get("timestamp", "")[:16]
            lines.append(f"{sev} {a.get('title', '?')}")
            if ts:
                lines.append(f"    <code>{ts}</code>")

    return truncate("\n".join(lines))


def generate_gateway_logs() -> str:
    """最近 Gateway 日誌（末尾 15 行）"""
    lines = [f"<b>📋 最近 Gateway 日誌</b>", f"{'━' * 25}"]

    log_path = "/root/.openclaw/logs/gateway.log"
    if not os.path.exists(log_path):
        lines.append("\n找不到 Gateway 日誌檔案")
        return "\n".join(lines)

    try:
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 3000))
            content = f.read().decode("utf-8", errors="replace")

        recent = content.strip().split("\n")[-15:]
        lines.append("")
        for line in recent:
            lines.append(f"<code>{_escape_html(line[:120])}</code>")
    except Exception as e:
        lines.append(f"\n讀取失敗: {_escape_html(str(e))}")

    return truncate("\n".join(lines))


def generate_health_check() -> str:
    """快速健康檢查（Gateway、Disk、Cron、狀態檔新鮮度）"""
    lines = [f"<b>🩺 健康檢查</b>", f"{'━' * 25}"]
    checks = []

    # Gateway
    try:
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
        r = subprocess.run(
            ["systemctl", "--user", "is-active", "openclaw-gateway"],
            capture_output=True, text=True, timeout=5, env=env,
        )
        gw_ok = r.stdout.strip() == "active"
        checks.append(("Gateway", gw_ok))
    except Exception:
        checks.append(("Gateway", False))

    # Disk
    try:
        st = os.statvfs("/")
        free_pct = st.f_bfree / st.f_blocks * 100
        checks.append(("Disk (>10% free)", free_pct > 10))
    except Exception:
        checks.append(("Disk", False))

    # Cron
    try:
        r = subprocess.run(["pgrep", "-x", "cron"], capture_output=True, timeout=3)
        checks.append(("Cron daemon", r.returncode == 0))
    except Exception:
        checks.append(("Cron daemon", False))

    # State file freshness
    state_file = "/root/.openclaw/monitoring/monitoring_state.json"
    try:
        age = time.time() - os.path.getmtime(state_file)
        checks.append(("監控狀態 (&lt;5min)", age < 300))
    except Exception:
        checks.append(("監控狀態", False))

    # Backup freshness
    try:
        bk_state = "/root/.openclaw/backups/backup_state.json"
        if os.path.exists(bk_state):
            with open(bk_state) as f:
                bs = json.load(f)
            fail = bs.get("consecutive_failures", 0)
            checks.append(("備份系統", fail == 0))
        else:
            checks.append(("備份系統", False))
    except Exception:
        checks.append(("備份系統", False))

    lines.append("")
    for name, ok in checks:
        icon = "✅" if ok else "❌"
        lines.append(f"  {icon} {name}")

    all_ok = all(ok for _, ok in checks)
    lines.append(f"\n{'🟢 所有檢查通過' if all_ok else '⚠️ 部分檢查未通過'}")
    lines.append(f"\n<code>{datetime.now(TZ_GMT8).strftime('%H:%M:%S')}</code>")

    return truncate("\n".join(lines))


def generate_backup_status() -> str:
    """備份狀態摘要"""
    lines = [f"<b>📊 備份狀態</b>", f"{'━' * 25}"]

    state_file = "/root/.openclaw/backups/backup_state.json"
    if not os.path.exists(state_file):
        lines.append("\n尚無備份紀錄")
        return "\n".join(lines)

    try:
        with open(state_file) as f:
            bs = json.load(f)

        last = bs.get("last_backup", "?")
        fail = bs.get("consecutive_failures", 0)
        total = bs.get("total_backups", 0)

        bk_dir = "/root/.openclaw/backups"
        bk_count = len([fn for fn in os.listdir(bk_dir)
                        if fn.startswith("backup_") and fn.endswith(".tar.gz")])

        lines.append("")
        lines.append(f"📦 最後備份: <code>{last[:19]}</code>")
        lines.append(f"📂 可用份數: {bk_count}")
        lines.append(f"📊 歷史總數: {total}")
        if fail > 0:
            lines.append(f"⚠️ 連續失敗: {fail}")
        else:
            lines.append(f"✅ 狀態正常")
    except Exception as e:
        lines.append(f"\n讀取失敗: {_escape_html(str(e))}")

    return truncate("\n".join(lines))


def generate_backup_list() -> str:
    """備份列表"""
    lines = [f"<b>📋 備份列表</b>", f"{'━' * 25}"]

    bk_dir = "/root/.openclaw/backups"
    if not os.path.exists(bk_dir):
        lines.append("\n尚無備份")
        return "\n".join(lines)

    files = sorted(
        [fn for fn in os.listdir(bk_dir) if fn.startswith("backup_") and fn.endswith(".tar.gz")],
        reverse=True,
    )

    if not files:
        lines.append("\n尚無備份檔案")
    else:
        lines.append(f"\n共 {len(files)} 份備份：\n")
        for fname in files[:7]:
            fpath = os.path.join(bk_dir, fname)
            size_kb = os.path.getsize(fpath) / 1024
            # 從檔名取時間 backup_YYYYMMDD_HHMMSS.tar.gz
            ts_part = fname.replace("backup_", "").replace(".tar.gz", "")
            if len(ts_part) >= 15:
                ts = f"{ts_part[:4]}-{ts_part[4:6]}-{ts_part[6:8]} {ts_part[9:11]}:{ts_part[11:13]}:{ts_part[13:15]}"
            else:
                ts = ts_part
            lines.append(f"  📦 <code>{ts}</code> ({size_kb:.0f} KB)")

    return truncate("\n".join(lines))


def generate_config_view(tenant_id: str) -> str:
    """查看當前生效設定"""
    lines = [f"<b>📋 當前設定</b>", f"{'━' * 25}"]

    try:
        from tenant_manager import TenantManager
        from config_governance import ConfigGovernance
        tm = TenantManager()
        gov = ConfigGovernance(tm)
        tenant = tm.get_tenant(tenant_id)
        if not tenant:
            lines.append("\n找不到租戶")
            return "\n".join(lines)

        config = gov.get_effective_config(tenant)
        lines.append("")
        for key, val in _flatten_config(config):
            lines.append(f"  <code>{_escape_html(str(key))}</code> = {_escape_html(str(val))}")
    except Exception as e:
        lines.append(f"\n讀取失敗: {_escape_html(str(e))}")

    return truncate("\n".join(lines))


def generate_config_history(tenant_id: str) -> str:
    """設定變更紀錄"""
    lines = [f"<b>📜 設定變更紀錄</b>", f"{'━' * 25}"]

    try:
        from tenant_manager import TenantManager
        from config_governance import ConfigGovernance
        tm = TenantManager()
        gov = ConfigGovernance(tm)
        tenant = tm.get_tenant(tenant_id)
        if not tenant:
            lines.append("\n找不到租戶")
            return "\n".join(lines)

        versions = gov.list_versions(tenant)
        if not versions:
            lines.append("\n尚無變更紀錄")
        else:
            lines.append(f"\n共 {len(versions)} 個版本：\n")
            for v in versions[-10:]:
                ts = str(v.get("timestamp", ""))[:16]
                user = v.get("user", "system")
                ver = v.get("version", "?")
                keys = [k for k, _ in v.get("patch_keys", [])]
                key_str = ", ".join(keys[:3])
                if len(keys) > 3:
                    key_str += f" +{len(keys) - 3}"
                lines.append(f"  v{ver} <code>{ts}</code> by {_escape_html(str(user))}")
                if key_str:
                    lines.append(f"      變更: {_escape_html(key_str)}")
    except Exception as e:
        lines.append(f"\n讀取失敗: {_escape_html(str(e))}")

    return truncate("\n".join(lines))


def generate_disk_report() -> str:
    """磁碟使用報告（委派至 log_governance）"""
    try:
        from log_governance import LogGovernanceEngine
        engine = LogGovernanceEngine()
        return truncate(engine.format_report_text())
    except Exception as e:
        return f"<b>📊 磁碟報告</b>\n\n讀取失敗: {_escape_html(str(e))}"


def generate_system_info(tenant_id: str, user_id: str) -> str:
    """系統資訊"""
    lines = [f"<b>ℹ️ 系統資訊</b>", f"{'━' * 25}"]

    # Uptime
    try:
        with open("/proc/uptime") as f:
            uptime_sec = int(float(f.read().split()[0]))
        days, rem = divmod(uptime_sec, 86400)
        hours, rem = divmod(rem, 3600)
        mins = rem // 60
        lines.append(f"\n⏱️ 系統運行: {days}天 {hours}時 {mins}分")
    except Exception:
        pass

    # Kernel
    try:
        kernel = subprocess.check_output(["uname", "-r"], text=True, timeout=3).strip()
        lines.append(f"🐧 Kernel: <code>{_escape_html(kernel)}</code>")
    except Exception:
        pass

    # Tenant
    lines.append(f"🏠 租戶: <code>{_escape_html(str(tenant_id))}</code>")

    # Role
    try:
        from rbac import RBACManager
        rbac = RBACManager()
        role = rbac.get_role(user_id, tenant_id)
        lines.append(f"👤 角色: <b>{role or 'unregistered'}</b>")
    except Exception:
        pass

    # Gateway
    try:
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
        r = subprocess.run(
            ["systemctl", "--user", "is-active", "openclaw-gateway"],
            capture_output=True, text=True, timeout=5, env=env,
        )
        gw_status = r.stdout.strip()
        lines.append(f"🖥️ Gateway: <b>{_escape_html(gw_status)}</b>")
    except Exception:
        pass

    # Backup count
    try:
        bk_dir = "/root/.openclaw/backups"
        bk_count = len([fn for fn in os.listdir(bk_dir)
                        if fn.startswith("backup_") and fn.endswith(".tar.gz")])
        lines.append(f"💾 備份: {bk_count} 份可用")
    except Exception:
        pass

    # Version
    lines.append(f"📦 引擎版本: v4.0")
    lines.append(f"\n<code>{datetime.now(TZ_GMT8).strftime('%Y-%m-%d %H:%M:%S')} GMT+8</code>")

    return truncate("\n".join(lines))


# ─── 工具 ────────────────────────────────────────────────

def _flatten_config(d: dict, prefix: str = "") -> list:
    """展平巢狀 dict 為 (key, value) 清單"""
    items = []
    for k, v in sorted(d.items()):
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.extend(_flatten_config(v, key))
        else:
            items.append((key, v))
    return items
