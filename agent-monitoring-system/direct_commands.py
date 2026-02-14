#!/usr/bin/env python3
"""
直接指令執行器 (Direct Command Executor)
═══════════════════════════════════════════
將原本依賴 AI 代理的 OpenClaw 指令轉為直接腳本執行，
提高穩定度並大幅縮短響應時間。

支援指令：
  /devreport    — 生成今日開發進度報告
  /costreport   — 查看 API 使用量與費用報告
  /gitlog       — 查看最近 Git 提交紀錄
  /gitdiff      — 查看目前未提交的變更
  /gitbranch    — 查看分支列表與目前分支
  /quickbackup  — 快速備份設定並推送到 GitHub

架構：
  OpenClaw customCommands → Telegram → menu_handler.handle_command()
  → direct_commands.execute() → 直接產出 HTML → Telegram API
"""

import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from html import escape as _esc

# ─── 路徑常量 ──────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = "/root/.openclaw/workspace"
TZ_GMT8 = timezone(timedelta(hours=8))


# ─── 工具函式 ──────────────────────────────────────────

def _run(cmd: str, cwd: str = WORKSPACE, timeout: int = 15) -> str:
    """安全執行 shell 指令，回傳 stdout 或錯誤訊息。"""
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=timeout
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if r.returncode != 0 and err:
            return f"⚠️ {_esc(err[:500])}"
        return out if out else "(無輸出)"
    except subprocess.TimeoutExpired:
        return "⚠️ 指令執行逾時"
    except Exception as e:
        return f"❌ 執行失敗: {_esc(str(e))}"


# ═══════════════════════════════════════════════════════════
# 指令實作
# ═══════════════════════════════════════════════════════════

def cmd_devreport() -> str:
    """生成今日開發進度報告。"""
    try:
        sys.path.insert(0, BASE_DIR)
        from dev_daily_report import build_report
        return build_report()
    except Exception as e:
        return f"❌ 開發日報產生失敗: {_esc(str(e))}"


def cmd_costreport() -> str:
    """查看 API 使用量與費用報告。"""
    try:
        sys.path.insert(0, BASE_DIR)
        from usage_cost_report import (
            load_env as ucr_load_env, load_state as ucr_load_state,
            get_openclaw_usage, calculate_cost, build_usage_report
        )
        ucr_load_env()
        state = ucr_load_state()
        usage = get_openclaw_usage()
        cost = calculate_cost(usage)
        history = state.get("history", [])
        return build_usage_report(usage, cost, history)
    except Exception as e:
        return f"❌ 費用報告產生失敗: {_esc(str(e))}"


def cmd_gitlog() -> str:
    """查看最近 20 筆 Git 提交紀錄。"""
    raw = _run("git --no-pager log --oneline --no-decorate -20")
    if raw.startswith(("⚠️", "❌")):
        return raw

    lines = []
    for line in raw.splitlines()[:20]:
        parts = line.split(" ", 1)
        if len(parts) == 2:
            sha, msg = parts
            lines.append(f"<code>{_esc(sha)}</code> {_esc(msg)}")
        else:
            lines.append(f"<code>{_esc(line)}</code>")

    branch = _run("git rev-parse --abbrev-ref HEAD").strip()
    header = f"<b>📜 Git Log</b> (分支: <code>{_esc(branch)}</code>)\n{'━' * 25}\n"
    return header + "\n".join(lines)


def cmd_gitdiff() -> str:
    """查看目前未提交的變更摘要。"""
    stat = _run("git --no-pager diff --stat")
    staged = _run("git --no-pager diff --cached --stat")
    untracked = _run("git ls-files --others --exclude-standard")

    parts = [f"<b>📝 Git Diff</b>\n{'━' * 25}"]

    if stat and not stat.startswith(("⚠️", "❌", "(無輸出)")):
        parts.append(f"\n<b>未暫存變更:</b>\n<pre>{_esc(stat[:1500])}</pre>")
    else:
        parts.append("\n✅ 無未暫存變更")

    if staged and not staged.startswith(("⚠️", "❌", "(無輸出)")):
        parts.append(f"\n<b>已暫存 (staged):</b>\n<pre>{_esc(staged[:1000])}</pre>")

    if untracked and not untracked.startswith(("⚠️", "❌", "(無輸出)")):
        files = untracked.splitlines()[:15]
        parts.append(f"\n<b>未追蹤檔案 ({len(untracked.splitlines())}):</b>")
        for f in files:
            parts.append(f"  • <code>{_esc(f)}</code>")
        if len(untracked.splitlines()) > 15:
            parts.append(f"  ... 還有 {len(untracked.splitlines()) - 15} 個")

    return "\n".join(parts)


def cmd_gitbranch() -> str:
    """查看分支列表與目前分支。"""
    raw = _run("git --no-pager branch -a --no-color")
    if raw.startswith(("⚠️", "❌")):
        return raw

    lines = []
    current = ""
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("* "):
            current = stripped[2:]
            lines.append(f"  👉 <b>{_esc(current)}</b> (目前)")
        elif "remotes/" in stripped:
            short = stripped.replace("remotes/origin/", "🌐 ")
            lines.append(f"  {_esc(short)}")
        else:
            lines.append(f"  {_esc(stripped)}")

    header = f"<b>🌿 Git Branches</b>\n{'━' * 25}\n"
    return header + "\n".join(lines[:30])


def cmd_quickbackup() -> str:
    """快速備份設定並推送到 GitHub。"""
    try:
        sys.path.insert(0, BASE_DIR)
        from backup_engine import BackupEngine
        engine = BackupEngine()

        # 建立本地備份
        manifest = engine.create_local_backup()
        result_parts = [
            f"<b>💾 快速備份</b>\n{'━' * 25}",
            f"✅ 本地備份完成",
            f"  📦 ID: <code>{_esc(manifest.backup_id)}</code>",
            f"  📁 檔案數: {manifest.file_count}",
            f"  💾 大小: {manifest.total_bytes / 1024:.1f} KB",
        ]

        # 推送到遠端
        ok, msg = engine.push_remote()
        if ok:
            result_parts.append(f"\n✅ 遠端推送成功")
        else:
            result_parts.append(f"\n⚠️ 遠端推送: {_esc(msg[:200])}")

        return "\n".join(result_parts)
    except Exception as e:
        return f"❌ 備份失敗: {_esc(str(e))}"


def cmd_info() -> str:
    """系統資訊概覽。"""
    import json as _json
    lines = [f"<b>ℹ️ 系統資訊</b>", f"{'━' * 25}"]

    # Uptime
    try:
        with open("/proc/uptime") as f:
            sec = int(float(f.read().split()[0]))
        d, rem = divmod(sec, 86400)
        h, rem = divmod(rem, 3600)
        m = rem // 60
        lines.append(f"\n⏱️ 系統運行: {d}天 {h}時 {m}分")
    except Exception:
        pass

    # Kernel
    kernel = _run("uname -r")
    if not kernel.startswith(("⚠", "❌")):
        lines.append(f"🐧 Kernel: <code>{_esc(kernel)}</code>")

    # Gateway
    gw = _run("systemctl --user is-active openclaw-gateway")
    gw_icon = "🟢" if gw.strip() == "active" else "🔴"
    lines.append(f"🖥️ Gateway: {gw_icon} <b>{_esc(gw.strip())}</b>")

    # Backup
    try:
        bk_dir = "/root/.openclaw/backups"
        bk_count = len([fn for fn in os.listdir(bk_dir)
                        if fn.startswith("backup_") and fn.endswith(".tar.gz")])
        lines.append(f"💾 備份: {bk_count} 份可用")
    except Exception:
        pass

    # OpenClaw version
    ver = _run("openclaw --version 2>/dev/null || echo unknown")
    lines.append(f"📦 OpenClaw: <code>{_esc(ver.splitlines()[0][:60])}</code>")

    lines.append(f"\n<code>{datetime.now(TZ_GMT8).strftime('%Y-%m-%d %H:%M:%S')} GMT+8</code>")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 指令路由
# ═══════════════════════════════════════════════════════════

DIRECT_COMMANDS = {
    "/devreport":    cmd_devreport,
    "/costreport":   cmd_costreport,
    "/gitlog":       cmd_gitlog,
    "/gitdiff":      cmd_gitdiff,
    "/gitbranch":    cmd_gitbranch,
    "/quickbackup":  cmd_quickbackup,
    "/info":         cmd_info,
}


def is_direct_command(cmd: str) -> bool:
    """檢查指令是否可以直接執行（不需 AI）。"""
    return cmd.lower() in DIRECT_COMMANDS


def execute(cmd: str) -> str:
    """
    執行直接指令並回傳 HTML 格式結果。

    Args:
        cmd: 指令字串，例如 "/gitlog"

    Returns:
        HTML 格式的結果文字

    Raises:
        KeyError: 不支援的指令
    """
    cmd = cmd.lower().split()[0].split("@")[0]
    handler = DIRECT_COMMANDS.get(cmd)
    if not handler:
        raise KeyError(f"不支援的直接指令: {cmd}")
    return handler()


# ═══════════════════════════════════════════════════════════
# CLI 介面 — 供 OpenClaw AI skill 直接呼叫
# ═══════════════════════════════════════════════════════════
#
# 用法:
#   python3 direct_commands.py devreport
#   python3 direct_commands.py costreport
#   python3 direct_commands.py gitlog
#   python3 direct_commands.py gitdiff
#   python3 direct_commands.py gitbranch
#   python3 direct_commands.py quickbackup
#   python3 direct_commands.py monitor       ← 監控儀表板

def cmd_monitor() -> str:
    """讀取快取的監控狀態並產生儀表板。"""
    try:
        state_file = "/root/.openclaw/monitoring/monitoring_state.json"
        if not os.path.exists(state_file):
            return "⚠️ 監控系統尚未執行第一次採集，請稍候 30 秒"
        import json as _json
        with open(state_file, "r", encoding="utf-8") as f:
            state = _json.load(f)
        sys.path.insert(0, BASE_DIR)
        from health_engine import render_dashboard
        return render_dashboard(state, html=False)
    except Exception as e:
        return f"❌ 儀表板產生失敗: {_esc(str(e))}"


# 完整指令表（含 /monitor 與 /info）
ALL_DIRECT = {
    "monitor":      cmd_monitor,
    "devreport":    cmd_devreport,
    "costreport":   cmd_costreport,
    "gitlog":       cmd_gitlog,
    "gitdiff":      cmd_gitdiff,
    "gitbranch":    cmd_gitbranch,
    "quickbackup":  cmd_quickbackup,
    "info":         cmd_info,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ALL_DIRECT:
        cmds = " | ".join(ALL_DIRECT.keys())
        print(f"用法: python3 {sys.argv[0]} <{cmds}>")
        sys.exit(1)

    print(ALL_DIRECT[sys.argv[1]]())
