#!/usr/bin/env python3
"""
選單處理器 (Menu Handler)
═══════════════════════════
職責：
  1. 處理 /menu、/monitor、/token、/backup、/config、/logs、/info、/help 等 Telegram 指令
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
from html import escape as _esc
from typing import Optional

from telegram_ui import (
    parse_cb, truncate,
    kb_main_menu, kb_monitor, kb_system, kb_backup, kb_config, kb_logs, kb_back,
    kb_confirm_restart, kb_token,
    page_home, page_monitor_menu, page_system_menu, page_backup_menu,
    page_config_menu, page_logs_menu, page_confirm_restart, page_help,
    page_token_menu,
    generate_perf_detail, generate_recent_alerts, generate_gateway_logs,
    generate_health_check, generate_backup_status, generate_backup_list,
    generate_config_view, generate_config_history, generate_disk_report,
    generate_system_info,
)


from command_registry import (
    SKELETON_SLASH, SKELETON_CALLBACK, skeleton_text,
)

from direct_commands import is_direct_command, execute as execute_direct

# ─── 骨架訊息 (Skeleton Message) ─────────────────────────
#
# 策略：先送出只有標題的佔位訊息（⏳ 載入中…），再以 editMessageText
# 回填實際資料。使用者體驗上達到「即時回應」的感覺。
#
# 兩條路徑都支援：
#   1. 斜線指令 (handle_command):   send skeleton → load → edit fill
#   2. 選單按鈕 (handle_menu_callback): edit skeleton → load → edit fill


def _send_skeleton(sender, cmd: str, keyboard=None) -> int:
    """斜線指令路徑：發送骨架佔位訊息，回傳 message_id。"""
    icon, title = SKELETON_SLASH.get(cmd, ("⏳", "載入中"))
    return sender.send(skeleton_text(icon, title), keyboard=keyboard)


def _fill_skeleton(sender, msg_id: int, content: str, keyboard=None):
    """用實際內容回填骨架訊息。若骨架發送失敗（msg_id=0），改為新發。"""
    if msg_id:
        sender.edit(msg_id, truncate(content), keyboard=keyboard)
    else:
        sender.send(truncate(content), keyboard=keyboard)


# ─── 指令處理 ────────────────────────────────────────────

def handle_command(sender, message: dict, rbac, tm, state: dict):
    """
    處理 Telegram /指令訊息。

    支援指令：
      /menu, /start  → 開啟主控面板
      /monitor       → 健康儀表板
      /token         → Token 成本摘要
      /backup        → 備份狀態
      /config        → 查看設定
      /logs          → 磁碟使用報告
      /info          → 系統資訊
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
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return

        score = state.get("health_score", 0)
        grade = state.get("health_grade", "?")
        ts = state.get("last_updated", "")
        sender.send(page_home(score, grade, ts), keyboard=kb_main_menu())
        print(f"📱 /menu 已回應 (user: {from_id})")

    elif cmd == "/monitor":
        perm = rbac.check_permission(from_id, tenant_id, "view_dashboard")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return

        msg_id = _send_skeleton(sender, cmd, keyboard=kb_back())
        try:
            from health_engine import render_dashboard
            dashboard = render_dashboard(state)
            _fill_skeleton(sender, msg_id, dashboard, keyboard=kb_back())
        except Exception as e:
            _fill_skeleton(sender, msg_id, f"❌ 載入儀表板失敗: {_esc(str(e))}", keyboard=kb_back())

    elif cmd == "/help":
        sender.send(page_help())

    elif cmd == "/token":
        perm = rbac.check_permission(from_id, tenant_id, "view_report")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return
        msg_id = _send_skeleton(sender, cmd, keyboard=kb_token())
        try:
            from token_governance import generate_token_summary
            _fill_skeleton(sender, msg_id, generate_token_summary(), keyboard=kb_token())
        except Exception as e:
            _fill_skeleton(sender, msg_id, f"❌ 載入失敗: {_esc(str(e))}", keyboard=kb_token())
        print(f"💰 /token 已回應 (user: {from_id})")

    elif cmd == "/backup":
        perm = rbac.check_permission(from_id, tenant_id, "view_dashboard")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return
        msg_id = _send_skeleton(sender, cmd, keyboard=kb_backup())
        try:
            _fill_skeleton(sender, msg_id, generate_backup_status(), keyboard=kb_backup())
        except Exception as e:
            _fill_skeleton(sender, msg_id, f"❌ 載入失敗: {_esc(str(e))}", keyboard=kb_backup())
        print(f"💾 /backup 已回應 (user: {from_id})")

    elif cmd == "/config":
        perm = rbac.check_permission(from_id, tenant_id, "view_config")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return
        msg_id = _send_skeleton(sender, cmd, keyboard=kb_config())
        try:
            _fill_skeleton(sender, msg_id, generate_config_view(tenant_id), keyboard=kb_config())
        except Exception as e:
            _fill_skeleton(sender, msg_id, f"❌ 載入失敗: {_esc(str(e))}", keyboard=kb_config())
        print(f"⚙️ /config 已回應 (user: {from_id})")

    elif cmd == "/logs":
        perm = rbac.check_permission(from_id, tenant_id, "view_logs")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return
        msg_id = _send_skeleton(sender, cmd, keyboard=kb_logs())
        try:
            _fill_skeleton(sender, msg_id, generate_disk_report(), keyboard=kb_logs())
        except Exception as e:
            _fill_skeleton(sender, msg_id, f"❌ 載入失敗: {_esc(str(e))}", keyboard=kb_logs())
        print(f"📝 /logs 已回應 (user: {from_id})")

    elif cmd == "/info":
        perm = rbac.check_permission(from_id, tenant_id, "view_dashboard")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return
        msg_id = _send_skeleton(sender, cmd, keyboard=kb_back())
        try:
            _fill_skeleton(sender, msg_id, generate_system_info(tenant_id, from_id), keyboard=kb_back())
        except Exception as e:
            _fill_skeleton(sender, msg_id, f"❌ 載入失敗: {_esc(str(e))}", keyboard=kb_back())
        print(f"ℹ️ /info 已回應 (user: {from_id})")

    elif is_direct_command(cmd):
        # 直接指令：devreport / costreport / gitlog / gitdiff / gitbranch / quickbackup
        perm = rbac.check_permission(from_id, tenant_id, "view_report")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return
        msg_id = _send_skeleton(sender, cmd, keyboard=kb_back())
        try:
            result = execute_direct(cmd)
            _fill_skeleton(sender, msg_id, result, keyboard=kb_back())
        except Exception as e:
            _fill_skeleton(sender, msg_id, f"❌ 執行失敗: {_esc(str(e))}", keyboard=kb_back())
        print(f"⚡ {cmd} 直接執行完成 (user: {from_id})")

    elif cmd == "/tenant":
        perm = rbac.check_permission(from_id, tenant_id, "manage_tenants")
        if not perm.allowed:
            sender.send(f"⛔ 權限不足: {_esc(str(perm.reason))}")
            return
        _handle_tenant_command(sender, text, from_id, tenant_id, tm, rbac)

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

    # ── 重資料頁面：先顯示骨架佔位（即時回應用戶點擊）──
    _skel = SKELETON_CALLBACK.get((page, action))
    if _skel and msg_id:
        _skel_icon, _skel_title = _skel
        sender.edit(msg_id, skeleton_text(_skel_icon, _skel_title))
        sender.answer_callback(cb_id)  # 立即移除按鈕載入動畫

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

    elif page == "tok":
        _page_token(show, check_perm, action)

    elif page == "info":
        show(generate_system_info(tenant_id, from_id), kb_back())

    elif not page and cb_data.startswith("/"):
        # slash command callback（主選單按鈕走 Gateway AI 路徑為主，
        # 但 health_engine 偶爾也會攔截到，此處做 fallback 處理）
        try:
            from direct_commands import is_direct_command, execute as execute_direct
            if is_direct_command(cb_data):
                show(execute_direct(cb_data), kb_back())
            else:
                sender.answer_callback(cb_id, "未知指令")
        except Exception as e:
            show(f"❌ {_esc(str(e))}", kb_back())

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
            show(f"❌ 載入失敗: {_esc(str(e))}", kb_back())

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


def _page_token(show, check_perm, action):
    """💰 Token 成本"""
    if not check_perm("view_report"):
        return

    if action == "summary":
        try:
            from token_governance import generate_token_summary
            show(truncate(generate_token_summary()), kb_back())
        except Exception as e:
            show(f"❌ 載入失敗: {_esc(str(e))}", kb_back())

    elif action == "detail":
        try:
            from token_governance import generate_token_detail
            show(truncate(generate_token_detail()), kb_back())
        except Exception as e:
            show(f"❌ 載入失敗: {_esc(str(e))}", kb_back())

    elif action == "hourly":
        try:
            from token_governance import generate_token_hourly
            show(truncate(generate_token_hourly()), kb_back())
        except Exception as e:
            show(f"❌ 載入失敗: {_esc(str(e))}", kb_back())

    elif action == "budget":
        try:
            from token_governance import generate_budget_status
            show(truncate(generate_budget_status()), kb_back())
        except Exception as e:
            show(f"❌ 載入失敗: {_esc(str(e))}", kb_back())

    else:
        # 子選單首頁
        show(page_token_menu(), kb_token())


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
            text = f"❌ <b>Gateway 重啟失敗</b>\n\n<code>{_esc(r.stderr[:300])}</code>"
            result = "failed"
    except Exception as exc:
        text = f"❌ <b>重啟錯誤</b>\n\n{_esc(str(exc))}"
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
            text = f"❌ <b>備份失敗</b>\n\n{_esc(str(manifest.error))}"
    except Exception as e:
        text = f"❌ <b>備份失敗</b>\n\n{_esc(str(e))}"

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
            text = f"✅ <b>備份驗證通過</b>\n\n{_esc(str(msg))}"
        else:
            text = f"❌ <b>備份驗證失敗</b>\n\n{_esc(str(msg))}"
    except Exception as e:
        text = f"❌ <b>驗證失敗</b>\n\n{_esc(str(e))}"

    if msg_id:
        sender.edit(msg_id, text, keyboard=kb_back())


# ─── /tenant 指令 ────────────────────────────────────────

def _handle_tenant_command(sender, text: str, from_id: str, tenant_id: str, tm, rbac):
    """
    處理 /tenant 指令族。

    用法：
      /tenant list             — 列出所有租戶
      /tenant add <chat_id> [名稱]  — 新增租戶（自動配置 openclaw.json + 重啟 gateway）
      /tenant remove <chat_id> — 停用租戶（從 openclaw.json 移除，不刪資料）
      /tenant info <chat_id>   — 查看租戶詳情
      /tenant restore <chat_id> [backup_id] — 還原租戶備份
    """
    parts = text.split(maxsplit=3)
    sub = parts[1].lower() if len(parts) > 1 else ""

    if sub == "list":
        _tenant_list(sender, tm)

    elif sub == "add":
        if len(parts) < 3:
            sender.send("⚠️ 用法：<code>/tenant add &lt;chat_id&gt; [名稱]</code>")
            return
        chat_id = parts[2].strip()
        name = parts[3].strip() if len(parts) > 3 else ""
        _tenant_add(sender, tm, rbac, chat_id, name, from_id, tenant_id)

    elif sub == "remove" or sub == "rm":
        if len(parts) < 3:
            sender.send("⚠️ 用法：<code>/tenant remove &lt;chat_id&gt;</code>")
            return
        chat_id = parts[2].strip()
        _tenant_remove(sender, tm, chat_id, from_id, tenant_id)

    elif sub == "info":
        if len(parts) < 3:
            sender.send("⚠️ 用法：<code>/tenant info &lt;chat_id&gt;</code>")
            return
        chat_id = parts[2].strip()
        _tenant_info(sender, tm, chat_id)

    elif sub == "restore":
        if len(parts) < 3:
            sender.send("⚠️ 用法：<code>/tenant restore &lt;chat_id&gt; [backup_id]</code>")
            return
        chat_id = parts[2].strip()
        backup_id = parts[3].strip() if len(parts) > 3 else None
        _tenant_restore(sender, tm, chat_id, backup_id)

    else:
        sender.send(
            "<b>🏠 租戶管理</b>\n"
            f"{'━' * 25}\n"
            "<code>/tenant list</code>  — 列出所有租戶\n"
            "<code>/tenant add &lt;id&gt; [名稱]</code>  — 新增\n"
            "<code>/tenant remove &lt;id&gt;</code>  — 停用\n"
            "<code>/tenant info &lt;id&gt;</code>  — 詳情\n"
            "<code>/tenant restore &lt;id&gt; [備份]</code>  — 還原"
        )


def _tenant_list(sender, tm):
    """列出所有租戶"""
    tenants = tm.get_all_tenants()
    if not tenants:
        sender.send("📭 目前無註冊租戶")
        return

    lines = [f"<b>🏠 租戶列表</b> ({len(tenants)} 個)", f"{'━' * 25}"]
    for t in tenants:
        status = "🟢" if t.enabled else "🔴"
        ws = t.workspace_dir()
        ws_exists = "✅" if os.path.isdir(ws) else "❌"
        lines.append(
            f"{status} <code>{t.chat_id}</code> {_esc(t.name)}\n"
            f"    ID: {_esc(t.tenant_id)}\n"
            f"    Workspace: {ws_exists} <code>{_esc(ws)}</code>"
        )
    sender.send("\n".join(lines))


def _tenant_add(sender, tm, rbac, chat_id: str, name: str, from_id: str, current_tenant_id: str):
    """新增租戶：register + provision config + restart gateway"""
    # 驗證 chat_id 格式
    if not chat_id.lstrip("-").isdigit():
        sender.send(f"❌ 無效的 chat_id: <code>{_esc(chat_id)}</code>")
        return

    # 檢查是否已存在
    existing = tm.get(chat_id)
    if existing and existing.enabled:
        sender.send(f"⚠️ 租戶 <code>{_esc(chat_id)}</code> 已存在且啟用中")
        return

    sender.send(f"⏳ 正在新增租戶 <code>{_esc(chat_id)}</code>...")

    try:
        # 1. 註冊租戶
        tenant = tm.register(chat_id, name=name or f"Tenant {chat_id}")
        step1 = f"✅ 租戶已註冊: {_esc(tenant.tenant_id)}"

        # 2. 配置 openclaw.json
        config_result = tm.provision_tenant_in_config(tenant)
        step2 = f"📝 Config: {_esc(config_result)}"

        # 3. 設定 RBAC（新租戶的 chat_id 自動成為 owner）
        try:
            rbac.assign_role(chat_id, "owner", tenant.tenant_id,
                             assigned_by=from_id, username=f"tenant_{chat_id}")
            step3 = f"✅ RBAC: {chat_id} = owner @ {tenant.tenant_id}"
        except Exception as e:
            step3 = f"⚠️ RBAC: {e}"

        # 4. 重啟 Gateway
        step4 = _restart_gateway_silent()

        # 5. 審計
        try:
            from audit import audit_log
            audit_log(current_tenant_id, "tenant_add", from_id, "",
                      f"新增租戶: {tenant.tenant_id} (chat_id={chat_id}, name={name})")
        except Exception:
            pass

        sender.send(
            f"<b>🏠 新增租戶完成</b>\n"
            f"{'━' * 25}\n"
            f"{step1}\n{step2}\n{step3}\n{step4}\n\n"
            f"<b>Workspace:</b> <code>{_esc(tenant.workspace_dir())}</code>\n"
            f"<b>Agent ID:</b> <code>tenant-{_esc(chat_id)}</code>"
        )
        print(f"🏠 /tenant add {chat_id} by {from_id}: success")

    except Exception as e:
        sender.send(f"❌ 新增租戶失敗:\n<code>{_esc(str(e))}</code>")
        print(f"🏠 /tenant add {chat_id} by {from_id}: FAILED - {e}")


def _tenant_remove(sender, tm, chat_id: str, from_id: str, current_tenant_id: str):
    """停用租戶：unregister + deprovision config + restart gateway"""
    tenant = tm.get(chat_id)
    if not tenant:
        sender.send(f"❌ 找不到租戶: <code>{_esc(chat_id)}</code>")
        return

    # 防止移除自己
    if chat_id == current_tenant_id.split(":")[-1]:
        sender.send("⛔ 無法移除自己的租戶")
        return

    sender.send(f"⏳ 正在停用租戶 <code>{_esc(chat_id)}</code>...")

    try:
        # 1. 停用租戶（不刪除資料）
        tm.unregister(chat_id)
        step1 = f"✅ 租戶已停用: {_esc(tenant.tenant_id)}"

        # 2. 從 openclaw.json 移除
        config_result = tm.deprovision_tenant_in_config(tenant)
        step2 = f"📝 Config: {_esc(config_result)}"

        # 3. 重啟 Gateway
        step3 = _restart_gateway_silent()

        # 4. 審計
        try:
            from audit import audit_log
            audit_log(current_tenant_id, "tenant_remove", from_id, "",
                      f"停用租戶: {tenant.tenant_id} (workspace 資料保留)")
        except Exception:
            pass

        sender.send(
            f"<b>🏠 停用租戶完成</b>\n"
            f"{'━' * 25}\n"
            f"{step1}\n{step2}\n{step3}\n\n"
            f"⚠️ Workspace 資料已保留於:\n"
            f"<code>{_esc(tenant.workspace_dir())}</code>"
        )
        print(f"🏠 /tenant remove {chat_id} by {from_id}: success")

    except Exception as e:
        sender.send(f"❌ 停用租戶失敗:\n<code>{_esc(str(e))}</code>")


def _tenant_info(sender, tm, chat_id: str):
    """查看租戶詳情"""
    tenant = tm.get(chat_id)
    if not tenant:
        sender.send(f"❌ 找不到租戶: <code>{_esc(chat_id)}</code>")
        return

    ws = tenant.workspace_dir()
    ws_exists = os.path.isdir(ws)
    ws_size = 0
    ws_files = 0
    if ws_exists:
        for root, dirs, files in os.walk(ws):
            ws_files += len(files)
            for f in files:
                try:
                    ws_size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass

    state_dir = tenant.state_dir()
    state_exists = os.path.isdir(state_dir)

    sender.send(
        f"<b>🏠 租戶詳情</b>\n"
        f"{'━' * 25}\n"
        f"<b>Tenant ID:</b> <code>{_esc(tenant.tenant_id)}</code>\n"
        f"<b>Chat ID:</b> <code>{_esc(tenant.chat_id)}</code>\n"
        f"<b>名稱:</b> {_esc(tenant.name)}\n"
        f"<b>類型:</b> {_esc(tenant.chat_type)}\n"
        f"<b>狀態:</b> {'🟢 啟用' if tenant.enabled else '🔴 停用'}\n"
        f"<b>建立:</b> {_esc(tenant.created_at[:19])}\n\n"
        f"<b>📁 Workspace</b>\n"
        f"  路徑: <code>{_esc(ws)}</code>\n"
        f"  存在: {'✅' if ws_exists else '❌'}\n"
        f"  檔案: {ws_files} 個, {ws_size / 1024:.0f} KB\n\n"
        f"<b>📊 Monitoring</b>\n"
        f"  路徑: <code>{_esc(state_dir)}</code>\n"
        f"  存在: {'✅' if state_exists else '❌'}"
    )


def _tenant_restore(sender, tm, chat_id: str, backup_id: str = None):
    """還原租戶備份"""
    tenant = tm.get(chat_id)
    if not tenant:
        sender.send(f"❌ 找不到租戶: <code>{_esc(chat_id)}</code>")
        return

    sender.send(f"⏳ 正在還原租戶 <code>{_esc(chat_id)}</code> 的備份...")

    try:
        from backup_engine import BackupEngine
        engine = BackupEngine()

        # 先列出可還原的檔案
        files = engine.list_tenant_files_in_backup(tenant.tenant_id, backup_id)
        if not files:
            bid = backup_id or "最新"
            sender.send(f"❌ 備份 ({bid}) 中無租戶 <code>{_esc(tenant.tenant_id)}</code> 的資料")
            return

        result = engine.restore_tenant(tenant.tenant_id, backup_id)

        if result.status == "success":
            text = (
                f"✅ <b>租戶還原完成</b>\n\n"
                f"租戶: <code>{_esc(tenant.tenant_id)}</code>\n"
                f"備份: <code>{_esc(result.backup_id)}</code>\n"
                f"還原: {result.files_restored} 檔\n"
                f"耗時: {result.duration_ms}ms"
            )
        else:
            text = (
                f"{'⚠️' if result.status == 'partial' else '❌'} "
                f"<b>租戶還原{'部分完成' if result.status == 'partial' else '失敗'}</b>\n\n"
                f"還原: {result.files_restored} | 失敗: {result.files_failed}\n"
                f"{'錯誤: ' + _esc(result.error) if result.error else ''}"
            )
        sender.send(text)

    except Exception as e:
        sender.send(f"❌ 還原失敗:\n<code>{_esc(str(e))}</code>")


def _restart_gateway_silent() -> str:
    """靜默重啟 Gateway，回傳狀態文字"""
    try:
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
        r = subprocess.run(
            ["systemctl", "--user", "restart", "openclaw-gateway"],
            capture_output=True, text=True, timeout=15, env=env,
        )
        if r.returncode == 0:
            return "🔄 Gateway 已重啟"
        return f"⚠️ Gateway 重啟失敗: {r.stderr.strip()[:100]}"
    except Exception as e:
        return f"⚠️ Gateway 重啟錯誤: {str(e)[:100]}"
