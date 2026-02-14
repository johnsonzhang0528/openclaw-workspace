#!/usr/bin/env python3
"""
備份與災難恢復引擎 (Backup & DR Engine)
═══════════════════════════════════════════
職責：
  1. L1 本地快照：定期壓縮關鍵資料 → /root/.openclaw/backups/
  2. L2 遠端推送：增量 git push 至 GitHub 私有 repo
  3. 完整性驗證：SHA-256 checksum + manifest
  4. 災難恢復：驗證並還原指定備份
  5. Telegram 通知：備份/還原結果推送

備份分層策略：
  ┌──────┬────────────────┬──────────────────┬──────────┐
  │ 層級 │ 目標           │ 內容             │ 保留     │
  ├──────┼────────────────┼──────────────────┼──────────┤
  │ L1   │ 本地 tar.gz    │ 狀態+配置+審計   │ 7 份     │
  │ L2   │ GitHub HTTPS   │ 工作區增量 push  │ 無限     │
  └──────┴────────────────┴──────────────────┴──────────┘

排除清單（敏感/可重建）：
  - .env（含 token/key）
  - identity/、credentials/
  - *.tmp、*.pyc、__pycache__
  - node_modules/、.git/
  - agents/main/sessions/*.jsonl（太大，且可重建）
"""

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TZ_GMT8 = timezone(timedelta(hours=8))

# ─── 常數 ──────────────────────────────────────────────────

OPENCLAW_ROOT = "/root/.openclaw"
BACKUP_DIR = os.path.join(OPENCLAW_ROOT, "backups")
MANIFEST_DIR = os.path.join(BACKUP_DIR, "manifests")
BACKUP_STATE_FILE = os.path.join(BACKUP_DIR, "backup_state.json")

# 備份保留數量
MAX_LOCAL_BACKUPS = 7

# 必須備份的路徑（相對於 OPENCLAW_ROOT）
BACKUP_INCLUDE = [
    # 監控系統狀態
    "monitoring/monitoring_state.json",
    "monitoring/tenants.json",
    "monitoring/tenants.json.bak",
    "monitoring/rbac.json",
    "monitoring/global_snapshot.json",
    "monitoring/gateway_restart_state.json",
    "monitoring/token_tracker_state.json",
    "monitoring/usage_report_state.json",
    # 租戶資料（state + audit + config）
    "monitoring/tenants/",
    # 工作區腳本（非 .env）
    "workspace/agent-monitoring-system/*.py",
    "workspace/agent-monitoring-system/*.sh",
    "workspace/agent-monitoring-system/*.md",
    # Cron 排程
    "cron/jobs.json",
    "cron/jobs.json.bak",
    # 核心配置
    "openclaw.json",
    "openclaw.json.bak",
    # 快捷鍵 / 子代理
    "shortcuts/",
    "subagents/",
    # SQLite 資料庫（小）
    "workspace/agent-monitoring-system/monitoring.db",
    # TodoList (now symlink → workspaces/ 涵蓋)
    "workspace/SOUL.md",
    # 租戶隔離 workspaces
    "workspaces/",
]

# 絕對排除清單（glob 模式）
BACKUP_EXCLUDE_PATTERNS = [
    "*.tmp",
    "*.pyc",
    "__pycache__",
    ".env",
    "identity/",
    "credentials/",
    "agents/main/sessions/",
    ".git/",
    "node_modules/",
    "media/",
    "canvas/",
    "skills/marketplace/cache/",
    "devices/",
    "workspace/memory/",
]

# ─── 資料類別 ──────────────────────────────────────────────

@dataclass
class BackupManifest:
    """備份清單"""
    backup_id: str                    # YYYYMMDD_HHMMSS
    timestamp: str                    # ISO 8601
    backup_type: str                  # "local" / "remote"
    file_count: int = 0
    total_bytes: int = 0
    checksum_sha256: str = ""         # tar.gz 的 SHA-256
    files: List[Dict] = field(default_factory=list)  # [{path, size, sha256}]
    duration_ms: int = 0
    status: str = "pending"           # pending / success / failed
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "BackupManifest":
        return BackupManifest(**{k: v for k, v in d.items()
                                 if k in BackupManifest.__dataclass_fields__})


@dataclass
class RestoreResult:
    """還原結果"""
    backup_id: str
    timestamp: str
    files_restored: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    duration_ms: int = 0
    status: str = "pending"
    error: str = ""
    details: List[str] = field(default_factory=list)


# ─── 備份引擎 ──────────────────────────────────────────────

class BackupEngine:
    """本地備份引擎"""

    def __init__(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.makedirs(MANIFEST_DIR, exist_ok=True)
        self._state = self._load_state()

    def _load_state(self) -> dict:
        if os.path.exists(BACKUP_STATE_FILE):
            try:
                with open(BACKUP_STATE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_backup": None,
            "last_backup_id": None,
            "total_backups": 0,
            "last_verify": None,
            "consecutive_failures": 0,
        }

    def _save_state(self):
        tmp = BACKUP_STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)
        os.replace(tmp, BACKUP_STATE_FILE)

    # ─── L1: 本地備份 ────────────────────────────────────

    def create_local_backup(self) -> BackupManifest:
        """
        建立本地 tar.gz 備份。
        
        流程：
          1. 收集所有備份檔案
          2. 建立 tar.gz
          3. 計算 SHA-256
          4. 寫入 manifest
          5. 清理舊備份
        """
        t0 = time.monotonic()
        now = datetime.now(TZ_GMT8)
        backup_id = now.strftime("%Y%m%d_%H%M%S")
        tar_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}.tar.gz")

        manifest = BackupManifest(
            backup_id=backup_id,
            timestamp=now.isoformat(),
            backup_type="local",
        )

        try:
            # 收集檔案
            files_to_backup = self._collect_backup_files()
            if not files_to_backup:
                manifest.status = "failed"
                manifest.error = "無檔案可備份"
                return manifest

            # 建立 tar.gz
            with tarfile.open(tar_path, "w:gz", compresslevel=6) as tar:
                for abs_path, rel_path in files_to_backup:
                    try:
                        tar.add(abs_path, arcname=rel_path)
                        file_stat = os.stat(abs_path)
                        file_hash = self._sha256_file(abs_path)
                        manifest.files.append({
                            "path": rel_path,
                            "size": file_stat.st_size,
                            "sha256": file_hash,
                        })
                        manifest.file_count += 1
                        manifest.total_bytes += file_stat.st_size
                    except Exception as exc:
                        manifest.files.append({
                            "path": rel_path,
                            "error": str(exc),
                        })

            # 計算 tar.gz 的 checksum
            manifest.checksum_sha256 = self._sha256_file(tar_path)
            manifest.duration_ms = int((time.monotonic() - t0) * 1000)
            manifest.status = "success"

            # 寫入 manifest
            manifest_path = os.path.join(MANIFEST_DIR, f"manifest_{backup_id}.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

            # 更新狀態
            self._state["last_backup"] = now.isoformat()
            self._state["last_backup_id"] = backup_id
            self._state["total_backups"] = self._state.get("total_backups", 0) + 1
            self._state["consecutive_failures"] = 0
            self._save_state()

            # 清理舊備份
            self._cleanup_old_backups()

            print(f"✅ 備份完成: {manifest.file_count} 檔, "
                  f"{manifest.total_bytes / 1024:.0f} KB, "
                  f"{manifest.duration_ms}ms")
            print(f"   SHA-256: {manifest.checksum_sha256[:16]}...")
            print(f"   路徑: {tar_path}")

        except Exception as exc:
            manifest.status = "failed"
            manifest.error = str(exc)
            manifest.duration_ms = int((time.monotonic() - t0) * 1000)
            self._state["consecutive_failures"] = self._state.get("consecutive_failures", 0) + 1
            self._save_state()
            print(f"❌ 備份失敗: {exc}")

        return manifest

    def _collect_backup_files(self) -> List[Tuple[str, str]]:
        """收集所有需要備份的檔案，回傳 (abs_path, relative_path) 列表"""
        files = []
        seen = set()

        for pattern in BACKUP_INCLUDE:
            abs_pattern = os.path.join(OPENCLAW_ROOT, pattern)

            if pattern.endswith("/"):
                # 目錄：遞迴收集
                dir_path = abs_pattern.rstrip("/")
                if os.path.isdir(dir_path):
                    for root, dirs, filenames in os.walk(dir_path):
                        # 排除模式
                        dirs[:] = [d for d in dirs if not self._is_excluded(
                            os.path.relpath(os.path.join(root, d), OPENCLAW_ROOT)
                        )]
                        for fname in filenames:
                            fpath = os.path.join(root, fname)
                            rel = os.path.relpath(fpath, OPENCLAW_ROOT)
                            if rel not in seen and not self._is_excluded(rel):
                                files.append((fpath, rel))
                                seen.add(rel)
            elif "*" in pattern:
                # glob 模式
                import glob
                for fpath in glob.glob(abs_pattern):
                    if os.path.isfile(fpath):
                        rel = os.path.relpath(fpath, OPENCLAW_ROOT)
                        if rel not in seen and not self._is_excluded(rel):
                            files.append((fpath, rel))
                            seen.add(rel)
            else:
                # 單一檔案
                if os.path.isfile(abs_pattern):
                    rel = os.path.relpath(abs_pattern, OPENCLAW_ROOT)
                    if rel not in seen:
                        files.append((abs_pattern, rel))
                        seen.add(rel)

        return files

    def _is_excluded(self, rel_path: str) -> bool:
        """檢查路徑是否在排除清單中"""
        for pattern in BACKUP_EXCLUDE_PATTERNS:
            if pattern.endswith("/"):
                if rel_path.startswith(pattern.rstrip("/")) or f"/{pattern.rstrip('/')}" in rel_path:
                    return True
            elif pattern.startswith("*."):
                ext = pattern[1:]
                if rel_path.endswith(ext):
                    return True
            elif pattern in rel_path:
                return True
        return False

    def _sha256_file(self, fpath: str) -> str:
        """計算檔案的 SHA-256"""
        h = hashlib.sha256()
        with open(fpath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _cleanup_old_backups(self):
        """保留最新 N 份備份，刪除舊的"""
        tar_files = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".tar.gz")],
            reverse=True,
        )
        for old_tar in tar_files[MAX_LOCAL_BACKUPS:]:
            try:
                os.remove(os.path.join(BACKUP_DIR, old_tar))
                # 同時刪除對應的 manifest
                bid = old_tar.replace("backup_", "").replace(".tar.gz", "")
                mf = os.path.join(MANIFEST_DIR, f"manifest_{bid}.json")
                if os.path.exists(mf):
                    os.remove(mf)
            except Exception:
                pass

    # ─── L2: 遠端推送 ────────────────────────────────────

    def push_remote(self) -> Tuple[bool, str]:
        """
        將工作區增量推送至 GitHub。
        使用已有的 git remote（HTTPS），不推送敏感檔案。
        """
        workspace_dir = os.path.join(OPENCLAW_ROOT, "workspace")
        if not os.path.isdir(os.path.join(workspace_dir, ".git")):
            return False, "工作區無 .git 目錄"

        try:
            # 檢查是否有 remote
            result = subprocess.run(
                ["git", "-C", workspace_dir, "remote", "-v"],
                capture_output=True, text=True, timeout=10,
            )
            if "origin" not in result.stdout:
                return False, "無 origin remote"

            # 確認 .gitignore 排除敏感檔案
            gitignore_path = os.path.join(workspace_dir, ".gitignore")
            self._ensure_gitignore(gitignore_path)

            # git add + commit
            subprocess.run(
                ["git", "-C", workspace_dir, "add", "-A"],
                capture_output=True, text=True, timeout=30,
            )

            # 檢查是否有變更
            status = subprocess.run(
                ["git", "-C", workspace_dir, "status", "--porcelain"],
                capture_output=True, text=True, timeout=10,
            )
            if not status.stdout.strip():
                return True, "無新變更"

            now = datetime.now(TZ_GMT8)
            commit_msg = f"backup: auto-backup {now.strftime('%Y-%m-%d %H:%M')} GMT+8"
            subprocess.run(
                ["git", "-C", workspace_dir, "commit", "-m", commit_msg],
                capture_output=True, text=True, timeout=30,
            )

            # git push
            push_result = subprocess.run(
                ["git", "-C", workspace_dir, "push", "origin", "main"],
                capture_output=True, text=True, timeout=120,
            )
            if push_result.returncode != 0:
                # 嘗試 master 分支
                push_result = subprocess.run(
                    ["git", "-C", workspace_dir, "push", "origin", "master"],
                    capture_output=True, text=True, timeout=120,
                )
            if push_result.returncode != 0:
                return False, f"push 失敗: {push_result.stderr.strip()}"

            return True, "推送成功"

        except subprocess.TimeoutExpired:
            return False, "操作逾時"
        except Exception as exc:
            return False, str(exc)

    def _ensure_gitignore(self, path: str):
        """確保 .gitignore 包含敏感檔案排除規則"""
        required_rules = [
            ".env",
            "*.tmp",
            "__pycache__/",
            "*.pyc",
            "identity/",
            "credentials/",
            "*.pem",
            "*.key",
            "*.secret",
            "device-auth.json",
            "telegram-pairing.json",
            "telegram-allowFrom.json",
        ]
        existing = set()
        if os.path.exists(path):
            with open(path, "r") as f:
                existing = set(line.strip() for line in f if line.strip() and not line.startswith("#"))

        missing = [r for r in required_rules if r not in existing]
        if missing:
            with open(path, "a") as f:
                f.write("\n# Auto-added by backup engine\n")
                for rule in missing:
                    f.write(rule + "\n")

    # ─── 驗證 ────────────────────────────────────────────

    def verify_backup(self, backup_id: str = None) -> Tuple[bool, str]:
        """
        驗證備份完整性。
        
        Args:
            backup_id: 指定備份 ID，None = 最新一份
            
        Returns:
            (通過, 訊息)
        """
        if backup_id is None:
            backup_id = self._state.get("last_backup_id")
        if not backup_id:
            return False, "無可驗證的備份"

        tar_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}.tar.gz")
        manifest_path = os.path.join(MANIFEST_DIR, f"manifest_{backup_id}.json")

        if not os.path.exists(tar_path):
            return False, f"備份檔不存在: {tar_path}"
        if not os.path.exists(manifest_path):
            return False, f"Manifest 不存在: {manifest_path}"

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            # 驗證 tar.gz checksum
            actual_hash = self._sha256_file(tar_path)
            expected_hash = manifest.get("checksum_sha256", "")
            if actual_hash != expected_hash:
                return False, f"Checksum 不符: 期望 {expected_hash[:16]}... 實際 {actual_hash[:16]}..."

            # 驗證 tar 可解壓
            with tarfile.open(tar_path, "r:gz") as tar:
                members = tar.getnames()
                expected_count = manifest.get("file_count", 0)
                # 容許少量差異（目錄條目可能不同）
                if len(members) < expected_count * 0.8:
                    return False, f"檔案數量不符: 期望 {expected_count}, 實際 {len(members)}"

            self._state["last_verify"] = datetime.now(TZ_GMT8).isoformat()
            self._save_state()

            tar_size = os.path.getsize(tar_path)
            return True, (f"✅ 驗證通過\n"
                         f"  備份 ID: {backup_id}\n"
                         f"  檔案數: {manifest.get('file_count', '?')}\n"
                         f"  壓縮大小: {tar_size / 1024:.0f} KB\n"
                         f"  SHA-256: {actual_hash[:16]}...")

        except Exception as exc:
            return False, f"驗證失敗: {exc}"

    # ─── 還原 ────────────────────────────────────────────

    def restore_backup(self, backup_id: str = None, target_dir: str = None,
                       dry_run: bool = False) -> RestoreResult:
        """
        還原備份。
        
        Args:
            backup_id: 備份 ID，None = 最新
            target_dir: 還原目標目錄，None = 原始位置 (OPENCLAW_ROOT)
            dry_run: True = 僅列出不還原
            
        Returns:
            RestoreResult
        """
        t0 = time.monotonic()

        if backup_id is None:
            backup_id = self._state.get("last_backup_id")

        result = RestoreResult(
            backup_id=backup_id or "unknown",
            timestamp=datetime.now(TZ_GMT8).isoformat(),
        )

        if not backup_id:
            result.status = "failed"
            result.error = "無可還原的備份"
            return result

        tar_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}.tar.gz")
        if not os.path.exists(tar_path):
            result.status = "failed"
            result.error = f"備份檔不存在: backup_{backup_id}.tar.gz"
            return result

        # 先驗證
        ok, msg = self.verify_backup(backup_id)
        if not ok:
            result.status = "failed"
            result.error = f"備份驗證失敗: {msg}"
            return result

        restore_to = target_dir or OPENCLAW_ROOT

        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                members = tar.getmembers()
                for member in members:
                    if member.isfile():
                        dest = os.path.join(restore_to, member.name)
                        if dry_run:
                            result.details.append(f"[DRY-RUN] 還原: {member.name}")
                            result.files_restored += 1
                            continue

                        try:
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            tar.extract(member, path=restore_to)
                            result.files_restored += 1
                            result.details.append(f"✅ {member.name}")
                        except Exception as exc:
                            result.files_failed += 1
                            result.details.append(f"❌ {member.name}: {exc}")

            result.duration_ms = int((time.monotonic() - t0) * 1000)
            result.status = "success" if result.files_failed == 0 else "partial"

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            result.duration_ms = int((time.monotonic() - t0) * 1000)

        return result

    # ─── 單一租戶還原 ─────────────────────────────────────

    def restore_tenant(self, tenant_id: str, backup_id: str = None,
                       dry_run: bool = False) -> RestoreResult:
        """
        還原單一租戶的資料（workspace + monitoring state）。

        從 L1 備份中只提取屬於該租戶的檔案：
          - workspaces/{tenant_dir}/...  (workspace 檔案)
          - monitoring/tenants/{tenant_dir}/... (監控狀態)

        Args:
            tenant_id: 租戶 ID，如 "telegram:1059505606"
            backup_id: 備份 ID，None = 最新
            dry_run:   True = 僅列出不還原
        """
        t0 = time.monotonic()

        if backup_id is None:
            backup_id = self._state.get("last_backup_id")

        result = RestoreResult(
            backup_id=backup_id or "unknown",
            timestamp=datetime.now(TZ_GMT8).isoformat(),
        )

        if not backup_id:
            result.status = "failed"
            result.error = "無可還原的備份"
            return result

        tar_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}.tar.gz")
        if not os.path.exists(tar_path):
            result.status = "failed"
            result.error = f"備份檔不存在: backup_{backup_id}.tar.gz"
            return result

        # 驗證
        ok, msg = self.verify_backup(backup_id)
        if not ok:
            result.status = "failed"
            result.error = f"備份驗證失敗: {msg}"
            return result

        # 租戶目錄前綴
        tenant_dir = tenant_id.replace(":", "_")
        prefixes = (
            f"workspaces/{tenant_dir}/",
            f"monitoring/tenants/{tenant_dir}/",
        )

        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                members = [
                    m for m in tar.getmembers()
                    if m.isfile() and any(m.name.startswith(p) for p in prefixes)
                ]

                if not members:
                    result.status = "failed"
                    result.error = f"備份中無租戶 {tenant_id} 的資料"
                    return result

                for member in members:
                    dest = os.path.join(OPENCLAW_ROOT, member.name)
                    if dry_run:
                        result.details.append(f"[DRY-RUN] 還原: {member.name}")
                        result.files_restored += 1
                        continue

                    try:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        tar.extract(member, path=OPENCLAW_ROOT)
                        result.files_restored += 1
                        result.details.append(f"✅ {member.name}")
                    except Exception as exc:
                        result.files_failed += 1
                        result.details.append(f"❌ {member.name}: {exc}")

            result.duration_ms = int((time.monotonic() - t0) * 1000)
            result.status = "success" if result.files_failed == 0 else "partial"

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            result.duration_ms = int((time.monotonic() - t0) * 1000)

        return result

    def list_tenant_files_in_backup(self, tenant_id: str, backup_id: str = None) -> List[str]:
        """列出備份中某租戶的所有檔案。"""
        if backup_id is None:
            backup_id = self._state.get("last_backup_id")
        if not backup_id:
            return []

        tar_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}.tar.gz")
        if not os.path.exists(tar_path):
            return []

        tenant_dir = tenant_id.replace(":", "_")
        prefixes = (
            f"workspaces/{tenant_dir}/",
            f"monitoring/tenants/{tenant_dir}/",
        )

        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                return [
                    m.name for m in tar.getmembers()
                    if m.isfile() and any(m.name.startswith(p) for p in prefixes)
                ]
        except Exception:
            return []

    # ─── 查詢 ────────────────────────────────────────────

    def list_backups(self) -> List[Dict]:
        """列出所有可用備份"""
        backups = []
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.startswith("backup_") and f.endswith(".tar.gz"):
                bid = f.replace("backup_", "").replace(".tar.gz", "")
                tar_path = os.path.join(BACKUP_DIR, f)
                manifest_path = os.path.join(MANIFEST_DIR, f"manifest_{bid}.json")

                info = {
                    "backup_id": bid,
                    "file": f,
                    "size_bytes": os.path.getsize(tar_path),
                    "size_kb": round(os.path.getsize(tar_path) / 1024, 1),
                }

                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r") as mf:
                            m = json.load(mf)
                        info["timestamp"] = m.get("timestamp", "")
                        info["file_count"] = m.get("file_count", 0)
                        info["checksum"] = m.get("checksum_sha256", "")[:16]
                        info["status"] = m.get("status", "unknown")
                    except Exception:
                        pass

                backups.append(info)

        return backups

    def get_status(self) -> Dict:
        """取得備份系統狀態"""
        backups = self.list_backups()
        return {
            "last_backup": self._state.get("last_backup"),
            "last_backup_id": self._state.get("last_backup_id"),
            "total_backups_created": self._state.get("total_backups", 0),
            "available_backups": len(backups),
            "last_verify": self._state.get("last_verify"),
            "consecutive_failures": self._state.get("consecutive_failures", 0),
            "backup_dir": BACKUP_DIR,
            "backups": backups[:5],  # 最新 5 份
        }

    def format_status_text(self) -> str:
        """格式化備份狀態為 Telegram HTML"""
        status = self.get_status()
        last_backup = status.get("last_backup", "從未備份")
        if last_backup and last_backup != "從未備份":
            last_backup = last_backup[:19]

        lines = [
            "<b>💾 備份系統狀態</b>",
            f"{'━' * 25}",
            f"<code>最後備份: {last_backup}</code>",
            f"<code>可用備份: {status['available_backups']} 份</code>",
            f"<code>歷史總數: {status['total_backups_created']}</code>",
            f"<code>最後驗證: {(status.get('last_verify') or '從未')[:19]}</code>",
        ]

        if status["consecutive_failures"] > 0:
            lines.append(f"⚠️ <b>連續失敗: {status['consecutive_failures']} 次</b>")

        if status["backups"]:
            lines.append("\n<b>📦 最近備份</b>")
            for b in status["backups"]:
                ts = b.get("timestamp", "")[:16]
                lines.append(
                    f"  {b['backup_id']}: {b.get('file_count', '?')} 檔, "
                    f"{b['size_kb']:.0f} KB"
                )

        return "\n".join(lines)


# ─── 整合入口（供 health_engine / cron 使用）─────────────

def run_scheduled_backup(notify_func=None) -> BackupManifest:
    """
    排程備份入口：
      1. 本地備份
      2. 驗證
      3. 遠端推送（如可用）
      4. 日誌輪轉
      5. 通知
    """
    engine = BackupEngine()

    # 1. 本地備份
    manifest = engine.create_local_backup()

    # 2. 驗證
    if manifest.status == "success":
        ok, verify_msg = engine.verify_backup(manifest.backup_id)
        if not ok:
            manifest.status = "verify_failed"
            manifest.error = verify_msg

    # 3. 遠端推送
    remote_msg = ""
    try:
        push_ok, push_msg = engine.push_remote()
        remote_msg = f"🌐 遠端: {push_msg}"
    except Exception as exc:
        remote_msg = f"🌐 遠端: ❌ {exc}"

    # 4. 日誌輪轉
    rotation_msg = ""
    try:
        from log_governance import LogGovernanceEngine, format_rotation_summary
        log_engine = LogGovernanceEngine()
        results = log_engine.run_rotation()
        rotation_msg = f"📋 日誌: {format_rotation_summary(results)}"
    except Exception as exc:
        rotation_msg = f"📋 日誌: ❌ {exc}"

    # 5. 審計記錄
    try:
        from audit import audit_log
        # 找到 primary tenant
        from tenant_manager import TenantManager
        tm = TenantManager()
        tenants = tm.get_active_tenants()
        if tenants:
            audit_log(
                tenant_id=tenants[0].tenant_id,
                action="backup_created",
                detail=f"本地備份 {manifest.backup_id}: {manifest.file_count} 檔, "
                       f"{manifest.total_bytes / 1024:.0f} KB, status={manifest.status}",
                component="backup",
            )
    except Exception:
        pass

    # 6. 通知
    if notify_func:
        status_icon = "✅" if manifest.status == "success" else "❌"
        text = (
            f"{status_icon} <b>排程備份完成</b>\n"
            f"{'━' * 25}\n"
            f"備份 ID: <code>{manifest.backup_id}</code>\n"
            f"檔案數: {manifest.file_count}\n"
            f"大小: {manifest.total_bytes / 1024:.0f} KB\n"
            f"耗時: {manifest.duration_ms}ms\n"
            f"SHA-256: <code>{manifest.checksum_sha256[:16]}...</code>\n\n"
            f"{remote_msg}\n"
            f"{rotation_msg}"
        )
        try:
            notify_func(text)
        except Exception:
            pass

    print(f"{remote_msg}")
    print(f"{rotation_msg}")

    return manifest


# ─── CLI 入口 ─────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw 備份與災難恢復引擎")
    sub = parser.add_subparsers(dest="command", help="指令")

    # backup
    sub_backup = sub.add_parser("backup", help="建立本地備份")

    # verify
    sub_verify = sub.add_parser("verify", help="驗證備份完整性")
    sub_verify.add_argument("--id", help="備份 ID")

    # restore
    sub_restore = sub.add_parser("restore", help="還原備份")
    sub_restore.add_argument("--id", help="備份 ID")
    sub_restore.add_argument("--target", help="還原目標目錄")
    sub_restore.add_argument("--dry-run", action="store_true", help="僅列出不還原")

    # list
    sub_list = sub.add_parser("list", help="列出可用備份")

    # status
    sub_status = sub.add_parser("status", help="備份系統狀態")

    # push
    sub_push = sub.add_parser("push", help="推送至 GitHub")

    # full (= backup + verify + push + rotate)
    sub_full = sub.add_parser("full", help="完整排程備份（備份+驗證+推送+日誌輪轉）")

    args = parser.parse_args()

    engine = BackupEngine()

    if args.command == "backup":
        engine.create_local_backup()

    elif args.command == "verify":
        ok, msg = engine.verify_backup(args.id)
        print(msg)
        sys.exit(0 if ok else 1)

    elif args.command == "restore":
        result = engine.restore_backup(
            backup_id=args.id,
            target_dir=args.target,
            dry_run=args.dry_run,
        )
        print(f"狀態: {result.status}")
        print(f"還原: {result.files_restored} 檔 | 失敗: {result.files_failed} | 耗時: {result.duration_ms}ms")
        if result.error:
            print(f"錯誤: {result.error}")
        for d in result.details[:20]:
            print(f"  {d}")
        sys.exit(0 if result.status == "success" else 1)

    elif args.command == "list":
        backups = engine.list_backups()
        if not backups:
            print("無可用備份")
            return
        for b in backups:
            ts = b.get("timestamp", "")[:19]
            print(f"  {b['backup_id']}  {b.get('file_count', '?'):>4} 檔  "
                  f"{b['size_kb']:>8.0f} KB  {b.get('status', '?')}")

    elif args.command == "status":
        status = engine.get_status()
        print(f"最後備份: {status.get('last_backup', '從未')}")
        print(f"可用備份: {status['available_backups']} 份")
        print(f"最後驗證: {status.get('last_verify', '從未')}")
        print(f"連續失敗: {status['consecutive_failures']}")

    elif args.command == "push":
        ok, msg = engine.push_remote()
        print(f"{'✅' if ok else '❌'} {msg}")
        sys.exit(0 if ok else 1)

    elif args.command == "full":
        run_scheduled_backup()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
