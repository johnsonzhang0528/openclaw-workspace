#!/usr/bin/env python3
"""
選單處理器 (Menu Handler)
═══════════════════════════
職責：
  1. 處理 /menu、/monitor、/help 等 Telegram 指令
  2. 處理主控面板 callback button 點擊
  3. 整合 RBAC 權限檢查（每個操作前驗證）
  4. 整合審計日誌（高風險操作記錄）
  5. 所有導航都透過 editMessageText 更新原訊息，避免洗版

整合方式：
  health_engine.py 的 _process_updates() 會把：
  - /指令訊息 → handle_command()
  - m: 開頭的 callback → handle_menu_callback()
"""

import os
import subprocess
from typing import Optional

from telegram_ui import (
    parse_cb, truncate,
    kb_main_menu, kb_monitor, kb_system, kb_backup, kb_config, kb_logs, kb_back,
    kb_confirm_restart,
    page_home, page_monitor_menu, page_system_menu, page_backup_menu,
    page_config_menu, page_logs_menu, page_confirm_restart, page_help,
    generate_perf_detail, generate_recent_alerts, generate_gateway_logs,
    generate_health_check, generate_backup_status, generate_backup_list,
    generate_config_view, generate_config_history, generate_disk_report,
    generate_system_info,
)


# ─── 指令處理 ────────────────────────────────────────────

def handle_command(sender, message: dict, rbac, tm, state: dict):
    """
    處理 Telegram /指令訊息。

    支援指令：
      /menu, /start  → 開啟主控面板
      /monitor       → 健康儀表板
      /help          → 指令說明

    Args:
        sender:  TelegramSender 實例
        message: Telegram message object
        rbac:    RBACManager 實例
        tm:      TenantManager 實例
        state:   主租戶狀態 dict
    """
    text = (message.get("text") or "").strip()
    chat_id = str(message.get("chat", {}).get("id", sender.chat_id))
    from_id = str(message.get("from", {}).get("id", ""))
    tenant_id = f"telegram:{chat_id}"

    cmd = text.split()[0].lower().split("@")[0] if text else ""  # 去掉 @botname

    if cmd in ("/menu", "/start"):
        perm = rbac.check_permission(from_id, tenant_id, "view_menu")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {perm.reason}")
            return

        score = state.get("health_score", 0)
        grade = state.get("health_grade", "?")
        ts = state.get("last_updated", "")
        sender.send(page_home(score, grade, ts), keyboard=kb_main_menu())
        print(f"📱 /menu 已回應 (user: {from_id})")

    elif cmd == "/monitor":
        perm = rbac.check_permission(from_id, tenant_id, "view_dashboard")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {perm.reason}")
            return

        try:
            from health_engine import render_dashboard
            dashboard = render_dashboard(state)
            sender.send(truncate(dashboard), keyboard=kb_back())
        except Exception as e:
            sender.send(f"❌ 載入儀表板失敗: {e}")

    elif cmd == "/help":
        sender.send(page_help())

    # 其他未知指令 → 不回應（避免干擾 OpenClaw 本身的指令）


# ─── Callback 處理 ───────────────────────────────────────

def handle_menu_callback(sender, cq: dict, rbac, tm, state: dict):
    """
    處理主控面板 callback button 點擊。

    所有選單導航都使用 editMessageText 更新原訊息（edit-in-place），
    避免在對話中產生大量重複訊息。

    Args:
        sender: TelegramSender 實例
        cq:     Telegram callback_query object
        rbac:   RBACManager 實例
        tm:     TenantManager 實例
        state:  主租戶狀態 dict
    """
    cb_id = cq.get("id", "")
    cb_data = cq.get("data", "")
    msg_id = cq.get("message", {}).get("message_id")
    chat_id = str(cq.get("message", {}).get("chat", {}).get("id", sender.chat_id))
    from_info = cq.get("from", {})
    from_id = str(from_info.get("id", ""))
    from_username = from_info.get("username", "unknown")
    tenant_id = f"telegram:{chat_id}"

    page, action, arg = parse_cb(cb_data)

    # ── 工具函式 ──

    def show(text, keyboard=None):
        """編輯訊息（edit-in-place）+ 回應 callback"""
        if msg_id:
            sender.edit(msg_id, truncate(text), keyboard=keyboard)
        sender.answer_callback(cb_id)

    def check_perm(permission: str) -> bool:
        """權限檢查，失敗時自動回應 callback toast"""
        perm = rbac.check_permission(from_id, tenant_id, permission)
        if not perm.allowed:
            sender.answer_callback(cb_id, f"⛔ {perm.reason}")
            return False
        return True

    # ── 路由 ──

    if page == "home":
        _page_home(show, state)

    elif page == "mon":
        _page_monitor(show, check_perm, action, state)

    elif page == "sys":
        _page_system(sender, show, check_perm, action, arg, cb_id, msg_id,
                     from_id, from_username, tenant_id, state)

    elif page == "bak":
        _page_backup(sender, show, check_perm, action, cb_id, msg_id,
                     from_id, from_username, tenant_id)

    elif page == "cfg":
        _page_config(show, check_perm, action, tenant_id)

    elif page == "log":
        _page_logs(show, check_perm, action)

    elif page == "info":
        show(generate_system_info(tenant_id, from_id), kb_back())

    else:
        sender.answer_callback(cb_id, "未知操作")


# ─── 頁面路由實作 ────────────────────────────────────────

def _page_home(show, state):
    """主選單"""
    score = state.get("health_score", 0)
    grade = state.get("health_grade", "?")
    ts = state.get("last_updated", "")
    show(page_home(score, grade, ts), kb_main_menu())


def _page_monitor(show, check_perm, action, state):
    """監控中心"""
    if not check_perm("view_dashboard"):
        return

    if action == "dash":
        try:
            from health_engine import render_dashboard
            show(render_dashboard(state), kb_back())
        except Exception as e:
            show(f"❌ 載入失敗: {e}", kb_back())

    elif action == "perf":
        show(generate_perf_detail(), kb_back())

    elif action == "alerts":
        show(generate_recent_alerts(state), kb_back())

    else:
        # 子選單首頁
        score = state.get("health_score", 0)
        grade = state.get("health_grade", "?")
        show(page_monitor_menu(score, grade), kb_monitor())


def _page_system(sender, show, check_perm, action, arg, cb_id, msg_id,
                 from_id, from_username, tenant_id, state):
    """系統操作"""
    if action == "restart":
        if not check_perm("restart_gateway"):
            return

        if arg == "y":
            # 執行重啟
            sender.answer_callback(cb_id, "正在重啟 Gateway...")
            _do_restart(sender, msg_id, from_id, from_username, tenant_id, state)
            return
        else:
            # 顯示確認頁面
            show(page_confirm_restart(), kb_confirm_restart())

    elif action == "logs":
        if not check_perm("view_logs"):
            return
        show(generate_gateway_logs(), kb_back())

    elif action == "health":
        if not check_perm("view_health"):
            return
        show(generate_health_check(), kb_back())

    else:
        # 子選單首頁
        snap = state.get("snapshot", {})
        gw = snap.get("gateway_active", True)
        show(page_system_menu(gw), kb_system())


def _page_backup(sender, show, check_perm, action, cb_id, msg_id,
                 from_id, from_username, tenant_id):
    """備份管理"""
    if action == "now":
        if not check_perm("manage_backup"):
            return
        sender.answer_callback(cb_id, "正在執行備份...")
        _do_backup(sender, msg_id, from_id, from_username, tenant_id)
        return

    elif action == "verify":
        if not check_perm("manage_backup"):
            return
        sender.answer_callback(cb_id, "正在驗證...")
        _do_verify(sender, msg_id)
        return

    elif action == "list":
        if not check_perm("manage_backup"):
            return
        show(generate_backup_list(), kb_back())

    elif action == "status":
        if not check_perm("view_dashboard"):
            return
        show(generate_backup_status(), kb_back())

    else:
        # 子選單首頁
        show(page_backup_menu(), kb_backup())


def _page_config(show, check_perm, action, tenant_id):
    """設定管理"""
    if not check_perm("view_config"):
        return

    if action == "view":
        show(generate_config_view(tenant_id), kb_back())

    elif action == "history":
        show(generate_config_history(tenant_id), kb_back())

    else:
        show(page_config_menu(), kb_config())


def _page_logs(show, check_perm, action):
    """日誌報告"""
    if action == "disk":
        if not check_perm("view_dashboard"):
            return
        show(generate_disk_report(), kb_back())
    else:
        show(page_logs_menu(), kb_logs())


# ─── 操作執行 ────────────────────────────────────────────

def _do_restart(sender, msg_id, user_id, username, tenant_id, state):
    """執行 Gateway 重啟"""
    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"

    try:
        r = subprocess.run(
            ["systemctl", "--user", "restart", "openclaw-gateway"],
            capture_output=True, text=True, timeout=15, env=env,
        )
        if r.returncode == 0:
            text = (
                "✅ <b>Gateway 重啟成功</b>\n\n"
                "請稍候約 1 分鐘，系統會自動發送重啟完成通知"
            )
            result = "success"
            # 重設自癒計數（使用 health_engine 的統一函式）
            from health_engine import reset_self_heal_on_recovery
            reset_self_heal_on_recovery(state)
        else:
            text = f"❌ <b>Gateway 重啟失敗</b>\n\n<code>{r.stderr[:300]}</code>"
            result = "failed"
    except Exception as exc:
        text = f"❌ <b>重啟錯誤</b>\n\n{exc}"
        result = "error"

    if msg_id:
        sender.edit(msg_id, text, keyboard=kb_back())

    # 審計
    try:
        from audit import audit_restart
        audit_restart(tenant_id, user_id, username, "menu_button", result)
    except Exception:
        pass

    print(f"🔄 Gateway 重啟 by @{username}: {result}")


def _do_backup(sender, msg_id, user_id, username, tenant_id):
    """執行本地備份"""
    try:
        from backup_engine import BackupEngine
        engine = BackupEngine()
        manifest = engine.create_local_backup()

        if manifest.status == "success":
            text = (
                f"✅ <b>備份完成</b>\n\n"
                f"📦 ID: <code>{manifest.backup_id}</code>\n"
                f"📊 大小: {manifest.total_bytes / 1024:.0f} KB → "
                f"{os.path.getsize(os.path.join('/root/.openclaw/backups', f'backup_{manifest.backup_id}.tar.gz')) / 1024:.0f} KB\n"
                f"📝 檔案數: {manifest.file_count}\n"
                f"🔑 SHA-256: <code>{manifest.checksum_sha256[:16]}...</code>\n"
                f"⏱️ 耗時: {manifest.duration_ms}ms"
            )
        else:
            text = f"❌ <b>備份失敗</b>\n\n{manifest.error}"
    except Exception as e:
        text = f"❌ <b>備份失敗</b>\n\n{e}"

    if msg_id:
        sender.edit(msg_id, text, keyboard=kb_back())

    # 審計
    try:
        from audit import audit_log
        audit_log(tenant_id, "backup", user_id, username, "手動備份 (via menu)")
    except Exception:
        pass

    print(f"💾 手動備份 by @{username}")


def _do_verify(sender, msg_id):
    """驗證最新備份"""
    try:
        from backup_engine import BackupEngine
        engine = BackupEngine()
        ok, msg = engine.verify_backup()

        if ok:
            text = f"✅ <b>備份驗證通過</b>\n\n{msg}"
        else:
            text = f"❌ <b>備份驗證失敗</b>\n\n{msg}"
    except Exception as e:
        text = f"❌ <b>驗證失敗</b>\n\n{e}"

    if msg_id:
        sender.edit(msg_id, text, keyboard=kb_back())
