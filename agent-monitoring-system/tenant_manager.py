#!/usr/bin/env python3
"""
租戶管理核心 (Tenant Manager)
═══════════════════════════════
多租戶資料模型、註冊、查詢、目錄管理。

租戶識別規則：
  tenant_id = "telegram:{chat_id}"
  • 私聊: chat_id 為正數
  • 群組: chat_id 為負數
  • 頻道: chat_id 以 -100 開頭

租戶目錄：
  /root/.openclaw/monitoring/tenants/{tenant_id}/
    ├── state.json            ← 該租戶的監控狀態
    ├── audit.log             ← 操作審計
    ├── config.json           ← 租戶個別設定（覆蓋預設）
    └── error_events.jsonl    ← 錯誤紀錄
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

TZ_GMT8 = timezone(timedelta(hours=8))
BASE_DIR = "/root/.openclaw/monitoring"
TENANTS_DIR = os.path.join(BASE_DIR, "tenants")
TENANTS_REGISTRY = os.path.join(BASE_DIR, "tenants.json")
RBAC_FILE = os.path.join(BASE_DIR, "rbac.json")

# 預設租戶設定（可被個別租戶覆蓋）
DEFAULT_TENANT_SETTINGS = {
    "dashboard_enabled": True,
    "alerts_enabled": True,
    "daily_report_enabled": True,
    "usage_report_enabled": True,
    "auto_pin_dashboard": True,
    "compact_mode": False,
    "alert_cooldowns": {
        "gateway_down": 120,
        "cpu_high": 600,
        "memory_high": 600,
        "disk_high": 600,
        "load_high": 600,
        "cron_missing": 600,
    },
    "thresholds": {
        "cpu_percent": 80.0,
        "memory_percent": 85.0,
        "disk_percent": 90.0,
        "load_avg_1m": 6.0,
    },
    "features": {
        "self_heal": True,
        "error_tracking": True,
        "restart_button": True,
    },
}


# ─── 資料結構 ────────────────────────────────────────────

@dataclass
class Tenant:
    """租戶資料"""
    tenant_id: str                           # telegram:1059505606
    chat_id: str                             # 1059505606
    name: str = ""                           # 顯示名稱
    chat_type: str = "private"               # private / group / supergroup / channel
    enabled: bool = True                     # 是否啟用
    created_at: str = ""                     # ISO 8601
    settings: Dict[str, Any] = field(default_factory=dict)
    # 執行期狀態（不持久化到 tenants.json）
    dashboard_message_id: Optional[int] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(TZ_GMT8).isoformat()
        if not self.name:
            self.name = f"Chat {self.chat_id}"

    @staticmethod
    def make_id(chat_id: str) -> str:
        return f"telegram:{chat_id}"

    def get_setting(self, key: str, default=None):
        """取得租戶設定，若無則回退到預設"""
        # 支援巢狀 key: "thresholds.cpu_percent"
        parts = key.split(".")
        val = self.settings
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                val = None
                break
        if val is not None:
            return val
        # 回退到預設
        val = DEFAULT_TENANT_SETTINGS
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                return default
        return val if val is not None else default

    def state_dir(self) -> str:
        return os.path.join(TENANTS_DIR, self.tenant_id.replace(":", "_"))

    def state_file(self) -> str:
        return os.path.join(self.state_dir(), "state.json")

    def audit_file(self) -> str:
        return os.path.join(self.state_dir(), "audit.log")

    def error_log_file(self) -> str:
        return os.path.join(self.state_dir(), "error_events.jsonl")

    def config_file(self) -> str:
        return os.path.join(self.state_dir(), "config.json")

    def to_dict(self) -> dict:
        """序列化（排除執行期狀態）"""
        return {
            "tenant_id": self.tenant_id,
            "chat_id": self.chat_id,
            "name": self.name,
            "chat_type": self.chat_type,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "settings": self.settings,
        }


# ─── 租戶管理器 ──────────────────────────────────────────

class TenantManager:
    """
    租戶管理：CRUD、狀態隔離、設定覆蓋。
    
    使用方式：
        tm = TenantManager()
        tenants = tm.get_active_tenants()
        for t in tenants:
            state = tm.load_tenant_state(t)
            # ... 操作 ...
            tm.save_tenant_state(t, state)
    """

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._ensure_dirs()
        self._load_registry()

    def _ensure_dirs(self):
        os.makedirs(TENANTS_DIR, exist_ok=True)

    def _load_registry(self):
        """載入租戶註冊表"""
        if not os.path.exists(TENANTS_REGISTRY):
            # 首次啟動：從 .env 遷移預設租戶
            self._migrate_default_tenant()
            return

        try:
            with open(TENANTS_REGISTRY, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("tenants", []):
                t = Tenant(**{k: v for k, v in entry.items() if k in Tenant.__dataclass_fields__})
                self._tenants[t.tenant_id] = t
        except Exception as exc:
            print(f"⚠️ 載入租戶註冊表失敗: {exc}")
            # 嘗試從備份恢復（避免毀損導致重新遷移丟失租戶）
            backup = TENANTS_REGISTRY + ".bak"
            recovered = False
            if os.path.exists(backup):
                try:
                    with open(backup, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for entry in data.get("tenants", []):
                        t = Tenant(**{k: v for k, v in entry.items() if k in Tenant.__dataclass_fields__})
                        self._tenants[t.tenant_id] = t
                    if self._tenants:
                        print(f"✅ 已從備份恢復 {len(self._tenants)} 個租戶")
                        self._save_registry()
                        recovered = True
                except Exception:
                    pass
            if not recovered:
                self._migrate_default_tenant()

    def _migrate_default_tenant(self):
        """從 .env 遷移原始的單一租戶"""
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

        tenant = Tenant(
            tenant_id=Tenant.make_id(chat_id),
            chat_id=chat_id,
            name="Admin (Primary)",
            chat_type="private",
            enabled=True,
        )
        self._tenants[tenant.tenant_id] = tenant

        # 確保目錄存在
        os.makedirs(tenant.state_dir(), exist_ok=True)

        # 遷移全域 monitoring_state.json 到租戶目錄
        global_state = os.path.join(BASE_DIR, "monitoring_state.json")
        tenant_state = tenant.state_file()
        if os.path.exists(global_state) and not os.path.exists(tenant_state):
            try:
                import shutil
                shutil.copy2(global_state, tenant_state)
                print(f"📋 已遷移全域狀態到租戶 {tenant.tenant_id}")
            except Exception:
                pass

        # 遷移全域 error_events.jsonl
        global_errors = os.path.join(BASE_DIR, "error_events.jsonl")
        tenant_errors = tenant.error_log_file()
        if os.path.exists(global_errors) and not os.path.exists(tenant_errors):
            try:
                import shutil
                shutil.copy2(global_errors, tenant_errors)
            except Exception:
                pass

        self._save_registry()
        print(f"✅ 已遷移預設租戶: {tenant.tenant_id} ({tenant.name})")

    def _save_registry(self):
        """儲存租戶註冊表（含備份）"""
        # 先備份現有檔案
        if os.path.exists(TENANTS_REGISTRY):
            backup = TENANTS_REGISTRY + ".bak"
            try:
                import shutil
                shutil.copy2(TENANTS_REGISTRY, backup)
            except Exception:
                pass

        data = {
            "version": 1,
            "updated_at": datetime.now(TZ_GMT8).isoformat(),
            "tenants": [t.to_dict() for t in self._tenants.values()],
        }
        tmp = TENANTS_REGISTRY + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, TENANTS_REGISTRY)

    # ─── CRUD ────────────────────────────────────────────

    def register(self, chat_id: str, name: str = "", chat_type: str = "private",
                 settings: dict = None) -> Tenant:
        """註冊新租戶"""
        tenant_id = Tenant.make_id(chat_id)
        if tenant_id in self._tenants:
            return self._tenants[tenant_id]

        tenant = Tenant(
            tenant_id=tenant_id,
            chat_id=chat_id,
            name=name or f"Chat {chat_id}",
            chat_type=chat_type,
            settings=settings or {},
        )
        os.makedirs(tenant.state_dir(), exist_ok=True)
        self._tenants[tenant_id] = tenant
        self._save_registry()
        return tenant

    def unregister(self, chat_id: str) -> bool:
        """停用租戶（不刪除資料）"""
        tenant_id = Tenant.make_id(chat_id)
        if tenant_id not in self._tenants:
            return False
        self._tenants[tenant_id].enabled = False
        self._save_registry()
        return True

    def get(self, chat_id: str) -> Optional[Tenant]:
        """取得租戶"""
        return self._tenants.get(Tenant.make_id(chat_id))

    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def get_active_tenants(self) -> List[Tenant]:
        """取得所有啟用中的租戶"""
        return [t for t in self._tenants.values() if t.enabled]

    def get_all_tenants(self) -> List[Tenant]:
        return list(self._tenants.values())

    def update_settings(self, chat_id: str, settings: dict) -> bool:
        """更新租戶設定"""
        tenant = self.get(chat_id)
        if not tenant:
            return False
        _deep_merge(tenant.settings, settings)
        self._save_registry()
        # 同時持久化到租戶 config.json
        self._save_tenant_config(tenant)
        return True

    def _save_tenant_config(self, tenant: Tenant):
        """儲存租戶個別 config"""
        os.makedirs(tenant.state_dir(), exist_ok=True)
        cfg_file = tenant.config_file()
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(tenant.settings, f, indent=2, ensure_ascii=False)

    # ─── 狀態管理 ────────────────────────────────────────

    def load_tenant_state(self, tenant: Tenant) -> dict:
        """載入租戶監控狀態"""
        sf = tenant.state_file()
        if not os.path.exists(sf):
            return self._default_tenant_state(tenant)
        try:
            with open(sf, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self._default_tenant_state(tenant)

    def save_tenant_state(self, tenant: Tenant, state: dict):
        """儲存租戶監控狀態"""
        os.makedirs(tenant.state_dir(), exist_ok=True)
        sf = tenant.state_file()
        tmp = sf + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp, sf)

    @staticmethod
    def _default_tenant_state(tenant: Tenant) -> dict:
        return {
            "version": 2,
            "tenant_id": tenant.tenant_id,
            "last_updated": datetime.now(TZ_GMT8).isoformat(),
            "health_score": 100,
            "health_grade": "A",
            "snapshot": {},
            "alerts": {
                "last_sent": {},
                "active_alerts": [],
            },
            "self_heal": {
                "gateway_restart_count": 0,
                "last_restart_attempt": None,
            },
            "errors": {
                "recent": [],
                "today_count": 0,
                "today_date": datetime.now(TZ_GMT8).strftime("%Y-%m-%d"),
            },
            "gateway_prev_running": True,
            "dashboard_message_id": None,
            "last_update_id": 0,
        }

    # ─── 全域快照（供 /monitor 使用）───────────────────

    def save_global_snapshot(self, snapshot: dict, score: int, grade: str):
        """儲存全域快照（向後相容舊 monitoring_state.json）"""
        global_state = os.path.join(BASE_DIR, "monitoring_state.json")
        data = {
            "version": 2,
            "last_updated": datetime.now(TZ_GMT8).strftime("%Y-%m-%d %H:%M:%S"),
            "health_score": score,
            "health_grade": grade,
            "snapshot": snapshot,
            "tenant_count": len(self.get_active_tenants()),
        }
        tmp = global_state + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, global_state)


# ─── 工具 ────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict):
    """深度合併，override 覆蓋 base"""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
