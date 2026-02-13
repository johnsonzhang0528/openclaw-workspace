#!/usr/bin/env python3
"""
配置治理 (Config Governance)
═════════════════════════════
職責：
  1. 版本化配置管理（每次變更產生新版本）
  2. Schema 驗證（套用前檢查格式與邏輯）
  3. 套用 → 健康檢查 → 失敗自動回滾
  4. 查詢歷史版本與差異

配置版本存放：
  /root/.openclaw/monitoring/tenants/{tenant_id}/
    ├── config.json          ← 當前生效版本
    ├── config-v1.json       ← 歷史版本
    ├── config-v2.json
    └── ...
"""

import json
import os
import glob
import copy
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from tenant_manager import Tenant, TenantManager, DEFAULT_TENANT_SETTINGS
from audit import audit_config_change, audit_log

TZ_GMT8 = timezone(timedelta(hours=8))

# ─── Schema 定義 ─────────────────────────────────────────

# 支援的配置鍵與其型別/範圍
CONFIG_SCHEMA = {
    "dashboard_enabled":        {"type": bool},
    "alerts_enabled":           {"type": bool},
    "daily_report_enabled":     {"type": bool},
    "usage_report_enabled":     {"type": bool},
    "auto_pin_dashboard":       {"type": bool},
    "compact_mode":             {"type": bool},
    "alert_cooldowns.gateway_down":   {"type": (int, float), "min": 30, "max": 3600},
    "alert_cooldowns.cpu_high":       {"type": (int, float), "min": 60, "max": 7200},
    "alert_cooldowns.memory_high":    {"type": (int, float), "min": 60, "max": 7200},
    "alert_cooldowns.disk_high":      {"type": (int, float), "min": 60, "max": 7200},
    "alert_cooldowns.load_high":      {"type": (int, float), "min": 60, "max": 7200},
    "alert_cooldowns.cron_missing":   {"type": (int, float), "min": 60, "max": 7200},
    "thresholds.cpu_percent":         {"type": (int, float), "min": 10, "max": 100},
    "thresholds.memory_percent":      {"type": (int, float), "min": 10, "max": 100},
    "thresholds.disk_percent":        {"type": (int, float), "min": 10, "max": 100},
    "thresholds.load_avg_1m":         {"type": (int, float), "min": 0.5, "max": 100},
    "features.self_heal":             {"type": bool},
    "features.error_tracking":        {"type": bool},
    "features.restart_button":        {"type": bool},
}


# ─── 驗證 ────────────────────────────────────────────────

def validate_config_value(key: str, value: Any) -> Tuple[bool, str]:
    """
    驗證單一配置值。
    返回 (valid, error_message)
    """
    schema = CONFIG_SCHEMA.get(key)
    if not schema:
        return False, f"未知配置鍵: {key}"

    expected_type = schema["type"]
    if not isinstance(value, expected_type):
        type_name = expected_type.__name__ if isinstance(expected_type, type) else str(expected_type)
        return False, f"{key} 需要 {type_name} 型別，收到 {type(value).__name__}"

    if isinstance(value, (int, float)):
        if "min" in schema and value < schema["min"]:
            return False, f"{key} 最小值為 {schema['min']}，收到 {value}"
        if "max" in schema and value > schema["max"]:
            return False, f"{key} 最大值為 {schema['max']}，收到 {value}"

    return True, ""


def validate_config_patch(patch: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    驗證配置補丁（批次）。
    返回 (all_valid, error_messages)
    """
    errors = []
    for key, value in _flatten_dict(patch):
        ok, msg = validate_config_value(key, value)
        if not ok:
            errors.append(msg)
    return len(errors) == 0, errors


def _flatten_dict(d: dict, prefix: str = "") -> List[Tuple[str, Any]]:
    """展平巢狀 dict 為 dot-notation key"""
    items = []
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, full_key))
        else:
            items.append((full_key, v))
    return items


# ─── 配置治理器 ──────────────────────────────────────────

class ConfigGovernance:
    """
    配置治理流程：
      1. propose() — 產生草稿
      2. validate() — Schema 檢查
      3. apply() — 套用到租戶 + 產生版本號
      4. health_check() — 套用後健康檢查
      5. rollback() — 失敗時回滾到上一版
    
    使用方式：
        gov = ConfigGovernance(tenant_manager)
        ok, errors = gov.apply_config_change(
            tenant=tenant,
            patch={"thresholds": {"cpu_percent": 90}},
            user_id="123456",
            username="@admin",
        )
    """

    def __init__(self, tenant_manager: TenantManager):
        self.tm = tenant_manager

    def get_current_version(self, tenant: Tenant) -> int:
        """取得當前配置版本號"""
        config_dir = tenant.state_dir()
        if not os.path.exists(config_dir):
            return 0
        pattern = os.path.join(config_dir, "config-v*.json")
        versions = []
        for path in glob.glob(pattern):
            fname = os.path.basename(path)
            try:
                v = int(fname.replace("config-v", "").replace(".json", ""))
                versions.append(v)
            except ValueError:
                continue
        return max(versions) if versions else 0

    def get_effective_config(self, tenant: Tenant) -> dict:
        """取得生效的完整配置（預設 + 租戶覆蓋）"""
        merged = copy.deepcopy(DEFAULT_TENANT_SETTINGS)
        if tenant.settings:
            _deep_merge(merged, tenant.settings)
        return merged

    def apply_config_change(
        self,
        tenant: Tenant,
        patch: Dict[str, Any],
        user_id: str = "system",
        username: str = "",
        skip_health_check: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        套用配置變更，完整流程：驗證 → 備份 → 套用 → 健康檢查 → 失敗回滾。
        
        返回 (success, messages)
        """
        messages = []

        # 1. 驗證
        valid, errors = validate_config_patch(patch)
        if not valid:
            for err in errors:
                messages.append(f"❌ 驗證失敗: {err}")
            # 審計
            for key, value in _flatten_dict(patch):
                audit_config_change(
                    tenant.tenant_id, user_id, username,
                    key, "(current)", value, result="validation_failed"
                )
            return False, messages

        # 2. 備份當前版本
        current_version = self.get_current_version(tenant)
        new_version = current_version + 1
        old_config = copy.deepcopy(tenant.settings)

        backup_file = os.path.join(tenant.state_dir(), f"config-v{new_version}.json")
        os.makedirs(tenant.state_dir(), exist_ok=True)
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump({
                "version": new_version,
                "timestamp": datetime.now(TZ_GMT8).isoformat(),
                "user_id": user_id,
                "username": username,
                "before": old_config,
                "patch": patch,
            }, f, indent=2, ensure_ascii=False)

        # 3. 套用
        try:
            for key, value in _flatten_dict(patch):
                _set_nested(tenant.settings, key, value)
                # 審計每個變更
                old_val = _get_nested(old_config, key)
                audit_config_change(
                    tenant.tenant_id, user_id, username,
                    key, old_val, value, result="applied"
                )
            # 持久化
            self.tm.update_settings(tenant.chat_id, tenant.settings)
            messages.append(f"✅ 配置 v{new_version} 已套用")
        except Exception as exc:
            messages.append(f"❌ 套用失敗: {exc}")
            # 回滾
            tenant.settings = old_config
            self.tm.update_settings(tenant.chat_id, tenant.settings)
            messages.append("🔄 已自動回滾到上一版")
            audit_log(
                tenant.tenant_id, "config_rollback",
                user_id, username,
                f"自動回滾: {exc}", result="rollback"
            )
            return False, messages

        # 4. 健康檢查（可選）
        if not skip_health_check:
            healthy, health_msg = self._post_apply_health_check(tenant)
            if not healthy:
                messages.append(f"⚠️ 健康檢查失敗: {health_msg}")
                messages.append("🔄 正在回滾...")
                tenant.settings = old_config
                self.tm.update_settings(tenant.chat_id, tenant.settings)
                messages.append(f"🔄 已回滾到 v{current_version}")
                audit_log(
                    tenant.tenant_id, "config_rollback",
                    user_id, username,
                    f"健康檢查失敗回滾: {health_msg}", result="rollback"
                )
                return False, messages
            messages.append("✅ 健康檢查通過")

        return True, messages

    def rollback_to_version(self, tenant: Tenant, version: int,
                            user_id: str = "system", username: str = "") -> Tuple[bool, str]:
        """手動回滾到指定版本"""
        version_file = os.path.join(tenant.state_dir(), f"config-v{version}.json")
        if not os.path.exists(version_file):
            return False, f"版本 v{version} 不存在"

        try:
            with open(version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            old_config = data.get("before", {})
            tenant.settings = old_config
            self.tm.update_settings(tenant.chat_id, tenant.settings)

            audit_log(
                tenant.tenant_id, "config_rollback",
                user_id, username,
                f"手動回滾到 v{version}", result="success"
            )
            return True, f"✅ 已回滾到 v{version}"
        except Exception as exc:
            return False, f"❌ 回滾失敗: {exc}"

    def list_versions(self, tenant: Tenant) -> List[Dict]:
        """列出所有配置版本"""
        config_dir = tenant.state_dir()
        if not os.path.exists(config_dir):
            return []

        versions = []
        for path in sorted(glob.glob(os.path.join(config_dir, "config-v*.json"))):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                versions.append({
                    "version": data.get("version"),
                    "timestamp": data.get("timestamp"),
                    "user": data.get("username") or data.get("user_id"),
                    "patch_keys": list(_flatten_dict(data.get("patch", {}))),
                })
            except Exception:
                continue
        return versions

    def _post_apply_health_check(self, tenant: Tenant) -> Tuple[bool, str]:
        """套用後快速健康檢查"""
        # 基本驗證：設定結構是否合理
        effective = self.get_effective_config(tenant)

        # 檢查閾值邏輯
        thresholds = effective.get("thresholds", {})
        for key, val in thresholds.items():
            if isinstance(val, (int, float)):
                if val <= 0:
                    return False, f"閾值 {key} 不可 <= 0"

        # 檢查冷卻時間
        cooldowns = effective.get("alert_cooldowns", {})
        for key, val in cooldowns.items():
            if isinstance(val, (int, float)):
                if val < 10:
                    return False, f"冷卻時間 {key} 太短 (< 10s)"

        return True, "OK"


# ─── 工具 ────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict):
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _set_nested(d: dict, key: str, value: Any):
    """設定巢狀 dict 值 (dot notation)"""
    parts = key.split(".")
    current = d
    for p in parts[:-1]:
        if p not in current or not isinstance(current[p], dict):
            current[p] = {}
        current = current[p]
    current[parts[-1]] = value


def _get_nested(d: dict, key: str, default=None):
    """取得巢狀 dict 值"""
    parts = key.split(".")
    current = d
    for p in parts:
        if isinstance(current, dict):
            current = current.get(p)
        else:
            return default
    return current if current is not None else default
