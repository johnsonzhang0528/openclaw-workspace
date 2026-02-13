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


def enforce_retention(tenant_id: str = None, retention_days: int = 90) -> int:
    """
    強制執行審計日誌保留策略。
    移除超過 retention_days 的舊記錄。
    
    Args:
        tenant_id: 指定租戶，None = 全部租戶
        retention_days: 保留天數（預設 90）
        
    Returns:
        移除的記錄數
    """
    tenants_dir = os.path.join(BASE_DIR, "tenants")
    if not os.path.isdir(tenants_dir):
        return 0

    total_removed = 0
    cutoff = datetime.now(TZ_GMT8) - timedelta(days=retention_days)

    dirs = []
    if tenant_id:
        tid = tenant_id.replace(":", "_")
        d = os.path.join(tenants_dir, tid)
        if os.path.isdir(d):
            dirs.append(d)
    else:
        for name in os.listdir(tenants_dir):
            d = os.path.join(tenants_dir, name)
            if os.path.isdir(d):
                dirs.append(d)

    for tenant_dir in dirs:
        audit_file = os.path.join(tenant_dir, "audit.log")
        if not os.path.exists(audit_file):
            continue

        kept = []
        removed = 0
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts_str = entry.get("ts", "")
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str)
                            if ts < cutoff:
                                removed += 1
                                continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                    kept.append(line)

            if removed > 0:
                tmp = audit_file + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    for line in kept:
                        f.write(line + "\n")
                os.replace(tmp, audit_file)
                total_removed += removed

        except Exception as exc:
            print(f"⚠️ 審計日誌保留策略執行失敗 ({tenant_dir}): {exc}")

    return total_removed
