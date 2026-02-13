#!/usr/bin/env python3
"""
審計日誌 (Audit Logger)
═══════════════════════
職責：
  1. 記錄所有高風險操作（配置變更、重啟、角色變更）
  2. 每筆紀錄包含：操作者、時間、操作、差異、結果
  3. 不可篡改（append-only），每租戶一份

格式：JSONL（每行一筆 JSON 記錄）
保留期：90 天
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

TZ_GMT8 = timezone(timedelta(hours=8))
BASE_DIR = "/root/.openclaw/monitoring"


def audit_log(
    tenant_id: str,
    action: str,
    user_id: str = "system",
    username: str = "",
    detail: str = "",
    diff: Optional[Dict] = None,
    result: str = "success",
    component: str = "system",
):
    """
    寫入一筆審計記錄。
    
    Args:
        tenant_id: 租戶 ID
        action: 操作名稱 (e.g., "config_change", "restart_gateway", "role_assign")
        user_id: 執行者 Telegram user_id
        username: 執行者 @username
        detail: 操作描述
        diff: 變更差異 {"before": ..., "after": ...}
        result: 結果 ("success" / "failed" / "denied")
        component: 元件名稱
    """
    tenant_dir = os.path.join(BASE_DIR, "tenants", tenant_id.replace(":", "_"))
    os.makedirs(tenant_dir, exist_ok=True)
    audit_file = os.path.join(tenant_dir, "audit.log")

    entry = {
        "ts": datetime.now(TZ_GMT8).isoformat(),
        "tenant_id": tenant_id,
        "action": action,
        "user_id": str(user_id),
        "username": username,
        "detail": detail[:500],
        "result": result,
        "component": component,
    }
    if diff:
        entry["diff"] = diff

    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"⚠️ 審計記錄寫入失敗: {exc}")


def read_audit_log(tenant_id: str, last_n: int = 50) -> list:
    """讀取最近 N 筆審計記錄"""
    tenant_dir = os.path.join(BASE_DIR, "tenants", tenant_id.replace(":", "_"))
    audit_file = os.path.join(tenant_dir, "audit.log")
    if not os.path.exists(audit_file):
        return []

    entries = []
    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return []

    return entries[-last_n:]


def audit_config_change(
    tenant_id: str,
    user_id: str,
    username: str,
    config_key: str,
    old_value: Any,
    new_value: Any,
    result: str = "success",
):
    """配置變更專用審計"""
    audit_log(
        tenant_id=tenant_id,
        action="config_change",
        user_id=user_id,
        username=username,
        detail=f"變更 {config_key}",
        diff={"key": config_key, "before": old_value, "after": new_value},
        result=result,
        component="config_governance",
    )


def audit_restart(tenant_id: str, user_id: str, username: str, trigger: str, result: str):
    """Gateway 重啟審計"""
    audit_log(
        tenant_id=tenant_id,
        action="restart_gateway",
        user_id=user_id,
        username=username,
        detail=f"觸發方式: {trigger}",
        result=result,
        component="gateway",
    )


def audit_role_change(
    tenant_id: str,
    user_id: str,
    username: str,
    target_user_id: str,
    old_role: str,
    new_role: str,
    result: str = "success",
):
    """角色變更審計"""
    audit_log(
        tenant_id=tenant_id,
        action="role_change",
        user_id=user_id,
        username=username,
        detail=f"使用者 {target_user_id}: {old_role} → {new_role}",
        diff={"target_user": target_user_id, "before": old_role, "after": new_role},
        result=result,
        component="rbac",
    )


def audit_permission_denied(tenant_id: str, user_id: str, username: str, action: str, reason: str):
    """權限拒絕審計"""
    audit_log(
        tenant_id=tenant_id,
        action="permission_denied",
        user_id=user_id,
        username=username,
        detail=f"嘗試執行 {action}: {reason}",
        result="denied",
        component="rbac",
    )
