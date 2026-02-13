#!/usr/bin/env python3
"""
角色型存取控制 (RBAC)
═══════════════════════
職責：
  1. 管理租戶內使用者角色
  2. 驗證指令權限
  3. 支援高風險操作的雙重確認

角色層級（由高到低）：
  owner   → 租戶擁有者（首個 chat_id 持有人），不可被降級
  admin   → 管理員，可執行所有操作
  member  → 一般成員，可查看、使用基本功能
  viewer  → 觀看者，僅可讀取

權限矩陣：
  ┌──────────────┬───────┬───────┬────────┬────────┐
  │ 操作         │ owner │ admin │ member │ viewer │
  ├──────────────┼───────┼───────┼────────┼────────┤
  │ /monitor     │  ✅   │  ✅   │  ✅    │  ✅    │
  │ /menu        │  ✅   │  ✅   │  ✅    │  ✅    │
  │ /report      │  ✅   │  ✅   │  ✅    │  ❌    │
  │ /restart     │  ✅   │  ✅   │  ❌    │  ❌    │
  │ /config      │  ✅   │  ✅   │  ❌    │  ❌    │
  │ /backup      │  ✅   │  ✅   │  ❌    │  ❌    │
  │ /tenant add  │  ✅   │  ❌   │  ❌    │  ❌    │
  │ /tenant rm   │  ✅   │  ❌   │  ❌    │  ❌    │
  │ /rbac        │  ✅   │  ❌   │  ❌    │  ❌    │
  └──────────────┴───────┴───────┴────────┴────────┘
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set

TZ_GMT8 = timezone(timedelta(hours=8))
BASE_DIR = "/root/.openclaw/monitoring"
RBAC_FILE = os.path.join(BASE_DIR, "rbac.json")

# ─── 角色定義 ────────────────────────────────────────────

ROLE_HIERARCHY = ["viewer", "member", "admin", "owner"]

# 權限定義：每個權限最低需要的角色
PERMISSIONS = {
    # 讀取類
    "view_dashboard":       "viewer",
    "view_menu":            "viewer",
    "view_health":          "viewer",
    "view_logs":            "member",
    "view_errors":          "member",
    "view_report":          "member",
    "view_config":          "member",
    # 操作類
    "trigger_report":       "member",
    "force_refresh":        "member",
    # 管理類（高風險）
    "restart_gateway":      "admin",
    "modify_config":        "admin",
    "manage_backup":        "admin",
    "manage_alerts":        "admin",
    "exec_command":         "admin",
    # 超級管理
    "manage_tenants":       "owner",
    "manage_rbac":          "owner",
    "delete_data":          "owner",
}

# 高風險操作（需要二次確認或額外驗證）
HIGH_RISK_OPERATIONS = {
    "restart_gateway",
    "delete_data",
    "manage_tenants",
    "manage_rbac",
    "modify_config",
}


# ─── 資料結構 ────────────────────────────────────────────

@dataclass
class UserRole:
    """使用者在某租戶的角色"""
    user_id: str           # Telegram user_id (數字字串)
    username: str          # @username
    role: str              # owner / admin / member / viewer
    tenant_id: str         # 所屬租戶
    assigned_at: str = ""  # ISO 8601
    assigned_by: str = ""  # 誰指派的

    def __post_init__(self):
        if not self.assigned_at:
            self.assigned_at = datetime.now(TZ_GMT8).isoformat()
        if self.role not in ROLE_HIERARCHY:
            raise ValueError(f"無效角色: {self.role}")


@dataclass
class PermissionResult:
    """權限檢查結果"""
    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False  # 是否需要二次確認


# ─── RBAC 管理器 ─────────────────────────────────────────

class RBACManager:
    """
    角色型存取控制管理器。
    
    使用方式：
        rbac = RBACManager()
        result = rbac.check_permission("123456", "telegram:1059505606", "restart_gateway")
        if result.allowed:
            if result.requires_confirmation:
                # 發送確認按鈕
            else:
                # 直接執行
    """

    def __init__(self):
        self._roles: Dict[str, Dict[str, UserRole]] = {}  # tenant_id → {user_id → UserRole}
        self._load()

    def _load(self):
        if not os.path.exists(RBAC_FILE):
            self._migrate_default()
            return
        try:
            with open(RBAC_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("roles", []):
                role = UserRole(**{k: v for k, v in entry.items() if k in UserRole.__dataclass_fields__})
                self._roles.setdefault(role.tenant_id, {})[role.user_id] = role
        except Exception as exc:
            print(f"⚠️ 載入 RBAC 失敗: {exc}")
            self._migrate_default()

    def _migrate_default(self):
        """從 .env 遷移：原始 chat_id 的持有人設為 owner"""
        env_file = "/root/.openclaw/workspace/agent-monitoring-system/.env"
        chat_id = ""
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TELEGRAM_CHAT_ID="):
                        chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if not chat_id:
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not chat_id:
            return

        tenant_id = f"telegram:{chat_id}"
        # 在私聊中，chat_id == user_id
        role = UserRole(
            user_id=chat_id,
            username="owner",
            role="owner",
            tenant_id=tenant_id,
            assigned_by="system_migration",
        )
        self._roles[tenant_id] = {chat_id: role}
        self._save()
        print(f"✅ 已遷移預設 RBAC: user {chat_id} → owner @ {tenant_id}")

    def _save(self):
        all_roles = []
        for tenant_roles in self._roles.values():
            for role in tenant_roles.values():
                all_roles.append({
                    "user_id": role.user_id,
                    "username": role.username,
                    "role": role.role,
                    "tenant_id": role.tenant_id,
                    "assigned_at": role.assigned_at,
                    "assigned_by": role.assigned_by,
                })
        data = {
            "version": 1,
            "updated_at": datetime.now(TZ_GMT8).isoformat(),
            "roles": all_roles,
        }
        os.makedirs(BASE_DIR, exist_ok=True)
        tmp = RBAC_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, RBAC_FILE)

    # ─── 權限檢查 ────────────────────────────────────────

    def get_role(self, user_id: str, tenant_id: str) -> Optional[str]:
        """取得使用者在指定租戶的角色"""
        tenant_roles = self._roles.get(tenant_id, {})
        role_obj = tenant_roles.get(str(user_id))
        return role_obj.role if role_obj else None

    def check_permission(self, user_id: str, tenant_id: str, permission: str) -> PermissionResult:
        """
        檢查使用者是否有指定權限。
        
        返回 PermissionResult:
          - allowed: 是否允許
          - reason: 拒絕原因
          - requires_confirmation: 高風險操作需要二次確認
        """
        user_role = self.get_role(str(user_id), tenant_id)

        # 未註冊的使用者
        if not user_role:
            return PermissionResult(
                allowed=False,
                reason=f"使用者 {user_id} 未在此租戶中註冊"
            )

        # 未知權限
        required_role = PERMISSIONS.get(permission)
        if not required_role:
            return PermissionResult(
                allowed=False,
                reason=f"未知權限: {permission}"
            )

        # 角色層級比較
        user_level = ROLE_HIERARCHY.index(user_role)
        required_level = ROLE_HIERARCHY.index(required_role)

        if user_level < required_level:
            return PermissionResult(
                allowed=False,
                reason=f"需要 {required_role} 以上角色（目前: {user_role}）"
            )

        # 檢查是否為高風險操作
        needs_confirm = permission in HIGH_RISK_OPERATIONS
        return PermissionResult(
            allowed=True,
            requires_confirmation=needs_confirm,
        )

    def check_chat_permission(self, user_id: str, chat_id: str, permission: str) -> PermissionResult:
        """以 chat_id 查詢權限（自動轉換 tenant_id）"""
        tenant_id = f"telegram:{chat_id}"
        return self.check_permission(str(user_id), tenant_id, permission)

    # ─── 角色管理 ────────────────────────────────────────

    def assign_role(self, user_id: str, tenant_id: str, role: str,
                    username: str = "", assigned_by: str = "system") -> bool:
        """指派角色"""
        if role not in ROLE_HIERARCHY:
            return False

        role_obj = UserRole(
            user_id=str(user_id),
            username=username,
            role=role,
            tenant_id=tenant_id,
            assigned_by=assigned_by,
        )
        self._roles.setdefault(tenant_id, {})[str(user_id)] = role_obj
        self._save()
        return True

    def revoke_role(self, user_id: str, tenant_id: str) -> bool:
        """撤銷角色（不能撤銷 owner）"""
        tenant_roles = self._roles.get(tenant_id, {})
        uid = str(user_id)
        if uid not in tenant_roles:
            return False
        if tenant_roles[uid].role == "owner":
            return False  # owner 不可撤銷
        del tenant_roles[uid]
        self._save()
        return True

    def list_roles(self, tenant_id: str) -> List[Dict]:
        """列出租戶中所有使用者角色"""
        tenant_roles = self._roles.get(tenant_id, {})
        return [
            {
                "user_id": r.user_id,
                "username": r.username,
                "role": r.role,
                "assigned_at": r.assigned_at,
            }
            for r in tenant_roles.values()
        ]

    def get_owners(self, tenant_id: str) -> List[str]:
        """取得租戶的所有 owner user_id"""
        tenant_roles = self._roles.get(tenant_id, {})
        return [r.user_id for r in tenant_roles.values() if r.role == "owner"]

    def get_admins(self, tenant_id: str) -> List[str]:
        """取得所有 admin 以上（含 owner）"""
        tenant_roles = self._roles.get(tenant_id, {})
        admin_idx = ROLE_HIERARCHY.index("admin")
        return [r.user_id for r in tenant_roles.values()
                if ROLE_HIERARCHY.index(r.role) >= admin_idx]

    # ─── 快捷方法 ────────────────────────────────────────

    def is_admin(self, user_id: str, tenant_id: str) -> bool:
        role = self.get_role(str(user_id), tenant_id)
        if not role:
            return False
        return ROLE_HIERARCHY.index(role) >= ROLE_HIERARCHY.index("admin")

    def is_owner(self, user_id: str, tenant_id: str) -> bool:
        role = self.get_role(str(user_id), tenant_id)
        return role == "owner"
