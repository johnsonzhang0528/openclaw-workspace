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

Workspace 隔離：
  /root/.openclaw/workspaces/{tenant_id}/
    └── (OpenClaw agent 工作區，依 chat_id 隔離)
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
WORKSPACES_DIR = "/root/.openclaw/workspaces"
OPENCLAW_CONFIG = "/root/.openclaw/openclaw.json"
OPENCLAW_ROOT = "/root/.openclaw"

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
        "load_avg_1m": 8.0,
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
    workspace: str = ""                      # 隔離 workspace 路徑
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

    def workspace_dir(self) -> str:
        """取得租戶的隔離 workspace 路徑"""
        if self.workspace:
            return self.workspace
        # 預設根據 tenant_id 生成
        return os.path.join(WORKSPACES_DIR, self.tenant_id.replace(":", "_"))

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
            "workspace": self.workspace,
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

        ws_dir = os.path.join(WORKSPACES_DIR, f"telegram_{chat_id}")
        tenant = Tenant(
            tenant_id=Tenant.make_id(chat_id),
            chat_id=chat_id,
            name="Admin (Primary)",
            chat_type="private",
            enabled=True,
            workspace=ws_dir,
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

    # 新租戶 workspace 需要的 bootstrap 模板文件（從共享 workspace 複製）
    WORKSPACE_TEMPLATE_FILES = [
        "AGENTS.md", "BOOT.md", "BOOTSTRAP.md", "HEARTBEAT.md",
        "IDENTITY.md", "MEMORY.md", "SOUL.md", "TOOLS.md", "USER.md",
    ]

    # 新租戶 workspace 需要建立的子目錄
    WORKSPACE_INIT_DIRS = ["memory", "issues", "leo-projects"]

    # 新租戶 workspace 需要建立的初始檔案（路徑 → 預設內容）
    WORKSPACE_INIT_FILES = {
        "todolist.md": "# TodoList\n\n## 待處理\n\n## 已處理\n",
        "user-docs.md": "",
        "issues_index.json": '{"issues": []}',
        "development-progress.json": '{"projects": []}',
    }

    def register(self, chat_id: str, name: str = "", chat_type: str = "private",
                 settings: dict = None) -> Tenant:
        """註冊新租戶（含 workspace 自動佈建）"""
        tenant_id = Tenant.make_id(chat_id)
        if tenant_id in self._tenants:
            return self._tenants[tenant_id]

        ws_dir = os.path.join(WORKSPACES_DIR, tenant_id.replace(":", "_"))
        tenant = Tenant(
            tenant_id=tenant_id,
            chat_id=chat_id,
            name=name or f"Chat {chat_id}",
            chat_type=chat_type,
            settings=settings or {},
            workspace=ws_dir,
        )
        os.makedirs(tenant.state_dir(), exist_ok=True)
        os.makedirs(tenant.workspace_dir(), exist_ok=True)

        # Bootstrap workspace: 建立目錄、模板文件、初始檔案
        self._bootstrap_workspace(tenant)

        self._tenants[tenant_id] = tenant
        self._save_registry()
        return tenant

    def _bootstrap_workspace(self, tenant: "Tenant"):
        """
        為新租戶 workspace 建立完整的初始結構：
          1. 子目錄（memory/, issues/, leo-projects/）
          2. 模板文件（AGENTS.md, SOUL.md 等，從共享 workspace 複製）
          3. 初始資料檔（todolist.md, issues_index.json 等）
        跳過已存在的檔案，避免覆蓋既有租戶資料。
        """
        ws = tenant.workspace_dir()
        shared_ws = os.path.join(OPENCLAW_ROOT, "workspace")

        # 1. 子目錄
        for d in self.WORKSPACE_INIT_DIRS:
            os.makedirs(os.path.join(ws, d), exist_ok=True)

        # 2. 複製模板文件
        import shutil
        for fname in self.WORKSPACE_TEMPLATE_FILES:
            src = os.path.join(shared_ws, fname)
            dst = os.path.join(ws, fname)
            if not os.path.exists(dst) and os.path.isfile(src):
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    print(f"⚠️ 無法複製模板 {fname}: {e}")

        # 3. 初始資料檔
        for fname, content in self.WORKSPACE_INIT_FILES.items():
            dst = os.path.join(ws, fname)
            if not os.path.exists(dst):
                try:
                    with open(dst, "w", encoding="utf-8") as f:
                        f.write(content)
                except Exception as e:
                    print(f"⚠️ 無法建立初始檔案 {fname}: {e}")

    def ensure_workspace(self, tenant: Tenant) -> str:
        """確保租戶 workspace 目錄存在，回傳路徑"""
        ws = tenant.workspace_dir()
        os.makedirs(ws, exist_ok=True)
        return ws

    def get_all_workspace_dirs(self) -> List[str]:
        """取得所有啟用租戶的 workspace 路徑（供備份用）"""
        return [t.workspace_dir() for t in self.get_active_tenants()]

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

    # ─── OpenClaw 配置管理 ────────────────────────────────

    def provision_tenant_in_config(self, tenant: "Tenant") -> str:
        """
        在 openclaw.json 中新增租戶的 agent entry、binding、allowFrom。
        回傳操作摘要文字。

        修改項目：
          - agents.list: 新增 {id, name, workspace}
          - bindings:    新增 {agentId, match: {channel, peer}}
          - channels.telegram.allowFrom: 加入 chat_id (int)
        """
        import copy
        if not os.path.exists(OPENCLAW_CONFIG):
            return "❌ openclaw.json 不存在"

        with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # 備份
        backup_path = OPENCLAW_CONFIG + ".bak"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        agent_id = f"tenant-{tenant.chat_id}"
        ws_dir = tenant.workspace_dir()
        chat_id_int = int(tenant.chat_id)
        changes = []

        # 1. agents.list
        agents = cfg.setdefault("agents", {})
        agent_list = agents.setdefault("list", [])
        existing_ids = {a.get("id", "") for a in agent_list}
        if agent_id not in existing_ids:
            agent_list.append({
                "id": agent_id,
                "name": tenant.name or f"Tenant {tenant.chat_id}",
                "workspace": ws_dir,
            })
            changes.append(f"agents.list += {agent_id}")

        # 2. bindings
        bindings = cfg.setdefault("bindings", [])
        has_binding = any(
            b.get("agentId") == agent_id
            for b in bindings
        )
        if not has_binding:
            bindings.append({
                "agentId": agent_id,
                "match": {
                    "channel": "telegram",
                    "peer": {
                        "kind": "direct",
                        "id": str(tenant.chat_id),
                    }
                }
            })
            changes.append(f"bindings += peer:{tenant.chat_id}")

        # 3. allowFrom
        allow_from = cfg.get("channels", {}).get("telegram", {}).get("allowFrom", [])
        if chat_id_int not in allow_from:
            cfg.setdefault("channels", {}).setdefault("telegram", {}).setdefault("allowFrom", [])
            cfg["channels"]["telegram"]["allowFrom"].append(chat_id_int)
            changes.append(f"allowFrom += {chat_id_int}")

        if not changes:
            return "⚠️ 該租戶已在 openclaw.json 中"

        # 寫入
        tmp = OPENCLAW_CONFIG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, OPENCLAW_CONFIG)

        return "✅ " + ", ".join(changes)

    def deprovision_tenant_in_config(self, tenant: "Tenant") -> str:
        """
        從 openclaw.json 移除租戶的 agent entry、binding、allowFrom。
        不刪除 workspace 資料。回傳操作摘要文字。
        """
        if not os.path.exists(OPENCLAW_CONFIG):
            return "❌ openclaw.json 不存在"

        with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        backup_path = OPENCLAW_CONFIG + ".bak"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        agent_id = f"tenant-{tenant.chat_id}"
        chat_id_int = int(tenant.chat_id)
        changes = []

        # 1. 移除 agent entry
        agent_list = cfg.get("agents", {}).get("list", [])
        new_list = [a for a in agent_list if a.get("id") != agent_id]
        if len(new_list) < len(agent_list):
            cfg["agents"]["list"] = new_list
            changes.append(f"agents.list -= {agent_id}")

        # 2. 移除 binding
        bindings = cfg.get("bindings", [])
        new_bindings = [b for b in bindings if b.get("agentId") != agent_id]
        if len(new_bindings) < len(bindings):
            cfg["bindings"] = new_bindings
            changes.append(f"bindings -= {agent_id}")

        # 3. 移除 allowFrom
        allow_from = cfg.get("channels", {}).get("telegram", {}).get("allowFrom", [])
        if chat_id_int in allow_from:
            allow_from.remove(chat_id_int)
            changes.append(f"allowFrom -= {chat_id_int}")

        if not changes:
            return "⚠️ 該租戶不在 openclaw.json 中"

        tmp = OPENCLAW_CONFIG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, OPENCLAW_CONFIG)

        return "✅ " + ", ".join(changes)


# ─── 工具 ────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict):
    """深度合併，override 覆蓋 base"""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
