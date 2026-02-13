#!/usr/bin/env python3
"""
日誌治理引擎 (Log Governance)
════════════════════════════════
職責：
  1. 日誌輪轉：依據保留策略自動壓縮/刪除過期日誌
  2. 日誌清單：統一管理所有日誌來源與路徑
  3. 空間監控：追蹤日誌總量並告警
  4. 審計日誌保留：90 天不可刪除

保留策略：
  ┌─────────────┬──────────┬──────────────────────┐
  │ 類型        │ 保留天數 │ 動作                 │
  ├─────────────┼──────────┼──────────────────────┤
  │ 核心日誌    │ 30 天    │ 壓縮 7 天+, 刪除 30+ │
  │ 效能/監控   │ 7 天     │ 壓縮 3 天+, 刪除 7+  │
  │ 審計日誌    │ 90 天    │ 壓縮 30 天+, 刪除 90+│
  │ 暫存日誌    │ 3 天     │ 直接刪除             │
  │ 軟刪除會話  │ 3 天     │ 刪除 3+              │
  │ 孤立會話    │ 14 天    │ 刪除 14+（保護活躍） │
  │ Gateway 日誌│ 14 天    │ 刪除 14+             │
  └─────────────┴──────────┴──────────────────────┘
"""

import gzip
import glob
import json
import os
import shutil
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TZ_GMT8 = timezone(timedelta(hours=8))

# ─── 日誌來源定義 ───────────────────────────────────────────

@dataclass
class LogSource:
    """描述一個日誌來源"""
    name: str                         # 日誌名稱
    path: str                         # 檔案路徑或 glob 模式
    category: str                     # core / performance / audit / temp / session / gateway
    retain_days: int                  # 保留天數
    compress_after_days: int = 0      # N 天後壓縮（0 = 不壓縮）
    max_size_mb: float = 50.0         # 單檔最大 MB（超過觸發提前輪轉）
    is_glob: bool = False             # path 是否為 glob 模式
    rotatable: bool = True            # 是否可輪轉（append-only 純文字可以）


# 全系統日誌來源清單
LOG_SOURCES: List[LogSource] = [
    # ── 核心日誌 (30 天) ──
    LogSource(
        name="health_engine",
        path="/tmp/health_engine.log",
        category="core",
        retain_days=30,
        compress_after_days=7,
        max_size_mb=20.0,
    ),
    LogSource(
        name="dev_daily_report",
        path="/tmp/dev_daily_report.log",
        category="core",
        retain_days=30,
        compress_after_days=7,
        max_size_mb=10.0,
    ),
    LogSource(
        name="usage_cost_report",
        path="/tmp/usage_cost_report.log",
        category="core",
        retain_days=30,
        compress_after_days=7,
        max_size_mb=10.0,
    ),
    # ── 效能 / 監控 (7 天) ──
    LogSource(
        name="error_events",
        path="/root/.openclaw/monitoring/error_events.jsonl",
        category="performance",
        retain_days=7,
        compress_after_days=3,
        max_size_mb=10.0,
    ),
    LogSource(
        name="tenant_error_events",
        path="/root/.openclaw/monitoring/tenants/*/error_events.jsonl",
        category="performance",
        retain_days=7,
        compress_after_days=3,
        max_size_mb=10.0,
        is_glob=True,
    ),
    LogSource(
        name="check_restart",
        path="/tmp/check_restart.log",
        category="performance",
        retain_days=7,
        compress_after_days=3,
        max_size_mb=5.0,
    ),
    # ── 審計日誌 (90 天，不可提前刪除) ──
    LogSource(
        name="tenant_audit",
        path="/root/.openclaw/monitoring/tenants/*/audit.log",
        category="audit",
        retain_days=90,
        compress_after_days=30,
        max_size_mb=50.0,
        is_glob=True,
    ),
    # ── 暫存日誌 (3 天) ──
    LogSource(
        name="proactive_alerts_log",
        path="/tmp/proactive_alerts.log",
        category="temp",
        retain_days=3,
        max_size_mb=5.0,
    ),
    LogSource(
        name="unified_dashboard_log",
        path="/tmp/unified_dashboard.log",
        category="temp",
        retain_days=3,
        max_size_mb=5.0,
    ),
    LogSource(
        name="cleanup_session_log",
        path="/tmp/cleanup_sessions.log",
        category="temp",
        retain_days=3,
        max_size_mb=5.0,
    ),
    # ── 會話資料 ──
    # 已被 OpenClaw 軟刪除的會話（*.jsonl.deleted.*），3 天後可安全清除
    LogSource(
        name="sessions_deleted",
        path="/root/.openclaw/agents/main/sessions/*.jsonl.deleted.*",
        category="session",
        retain_days=3,
        is_glob=True,
        rotatable=False,
    ),
    # 孤立的會話檔（未被 sessions.json 引用），14 天後清除
    # ⚠️ 正在使用中的 active session 會被 _load_protected_session_files() 保護
    LogSource(
        name="sessions_orphaned",
        path="/root/.openclaw/agents/main/sessions/*.jsonl",
        category="session",
        retain_days=14,
        is_glob=True,
        rotatable=False,
    ),
    # ── Gateway 日誌 (14 天) ──
    LogSource(
        name="gateway_logs",
        path="/root/.openclaw/logs/*.log",
        category="gateway",
        retain_days=14,
        is_glob=True,
        rotatable=False,   # 由 gateway 自己管理格式，只做刪除
    ),
    # ── Cron 執行紀錄 (7 天) ──
    LogSource(
        name="cron_runs",
        path="/root/.openclaw/cron/runs/*.jsonl",
        category="performance",
        retain_days=7,
        is_glob=True,
        rotatable=False,
    ),
]


# ─── 輪轉結果 ──────────────────────────────────────────────

@dataclass
class RotationResult:
    """單次輪轉操作的結果"""
    source_name: str
    action: str            # "compressed" / "deleted" / "truncated" / "skipped" / "error"
    file_path: str
    original_size_bytes: int = 0
    new_size_bytes: int = 0
    detail: str = ""


# ─── 日誌治理引擎 ──────────────────────────────────────────

class LogGovernanceEngine:
    """日誌治理引擎：輪轉、壓縮、清除過期日誌"""

    def __init__(self, sources: List[LogSource] = None):
        self.sources = sources or LOG_SOURCES
        self._results: List[RotationResult] = []
        self._protected_files: set = set()

    def _load_protected_session_files(self) -> set:
        """
        讀取 sessions.json 找出所有活躍的 session 檔案路徑。
        這些檔案絕對不能被刪除，否則會中斷 MoltBot 的對話上下文。
        
        保護範圍：
          - sessions.json 本身
          - 所有被 sessions.json 引用的 .jsonl 檔案（包含 active session）
        """
        protected = set()
        sessions_dir = "/root/.openclaw/agents/main/sessions"
        sessions_index = os.path.join(sessions_dir, "sessions.json")

        # 保護 sessions.json 索引檔
        protected.add(sessions_index)

        if not os.path.exists(sessions_index):
            return protected

        try:
            with open(sessions_index, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, entry in data.items():
                sid = entry.get("sessionId", "")
                if sid:
                    session_file = os.path.join(sessions_dir, f"{sid}.jsonl")
                    protected.add(session_file)
        except Exception:
            # 解析失敗時保守處理：保護目錄下所有 .jsonl
            for fname in os.listdir(sessions_dir):
                if fname.endswith(".jsonl"):
                    protected.add(os.path.join(sessions_dir, fname))

        return protected

    def run_rotation(self, dry_run: bool = False) -> List[RotationResult]:
        """
        執行完整日誌輪轉。
        
        Args:
            dry_run: True = 僅報告不執行
            
        Returns:
            輪轉操作結果列表
        """
        self._results = []
        now = datetime.now(TZ_GMT8)

        # 載入受保護的 session 檔案清單（避免誤刪活躍對話）
        self._protected_files = self._load_protected_session_files()

        for src in self.sources:
            try:
                files = self._resolve_files(src)
                for fpath in files:
                    self._process_file(src, fpath, now, dry_run)
            except Exception as exc:
                self._results.append(RotationResult(
                    source_name=src.name,
                    action="error",
                    file_path=src.path,
                    detail=str(exc),
                ))

        return self._results

    def _resolve_files(self, src: LogSource) -> List[str]:
        """解析日誌來源的實際檔案路徑"""
        if src.is_glob:
            # glob 模式：展開所有匹配檔案
            files = glob.glob(src.path)
            # 也檢查已壓縮的版本
            files += glob.glob(src.path + ".gz")
            files += glob.glob(src.path.replace("*", "**/*") if "**" not in src.path else "")
            # 去重
            return list(set(f for f in files if f and os.path.isfile(f)))
        else:
            result = []
            if os.path.exists(src.path):
                result.append(src.path)
            # 也找已輪轉的歷史檔
            rotated_pattern = src.path + ".*"
            result += glob.glob(rotated_pattern)
            return list(set(f for f in result if os.path.isfile(f)))

    def _process_file(self, src: LogSource, fpath: str, now: datetime, dry_run: bool):
        """處理單一檔案：判斷壓縮或刪除"""
        # 保護活躍的 session 檔案，絕不刪除
        if fpath in self._protected_files:
            self._results.append(RotationResult(
                source_name=src.name, action="skipped",
                file_path=fpath,
                detail="受保護的活躍 session（sessions.json 引用中）",
            ))
            return

        try:
            stat = os.stat(fpath)
        except OSError:
            return

        file_age_days = (now.timestamp() - stat.st_mtime) / 86400
        file_size_mb = stat.st_size / (1024 * 1024)
        is_compressed = fpath.endswith(".gz")

        # ── 刪除判斷：超過保留天數 ──
        if file_age_days > src.retain_days:
            if not dry_run:
                try:
                    os.remove(fpath)
                except OSError as e:
                    self._results.append(RotationResult(
                        source_name=src.name, action="error",
                        file_path=fpath, detail=f"刪除失敗: {e}",
                    ))
                    return
            self._results.append(RotationResult(
                source_name=src.name, action="deleted",
                file_path=fpath, original_size_bytes=stat.st_size,
                detail=f"超過 {src.retain_days} 天 (已存 {file_age_days:.1f} 天)",
            ))
            return

        # ── 壓縮判斷：超過壓縮天數且尚未壓縮 ──
        if (src.compress_after_days > 0
                and file_age_days > src.compress_after_days
                and not is_compressed
                and src.rotatable):
            gz_path = fpath + ".gz"
            if not dry_run:
                try:
                    self._compress_file(fpath, gz_path)
                except Exception as e:
                    self._results.append(RotationResult(
                        source_name=src.name, action="error",
                        file_path=fpath, detail=f"壓縮失敗: {e}",
                    ))
                    return
            gz_size = os.path.getsize(gz_path) if not dry_run and os.path.exists(gz_path) else 0
            self._results.append(RotationResult(
                source_name=src.name, action="compressed",
                file_path=fpath, original_size_bytes=stat.st_size,
                new_size_bytes=gz_size,
                detail=f"存在 {file_age_days:.1f} 天",
            ))
            return

        # ── 大小輪轉：超過單檔上限（copytruncate 語義）──
        if file_size_mb > src.max_size_mb and src.rotatable and not is_compressed:
            rotated_path = f"{fpath}.{now.strftime('%Y%m%d_%H%M%S')}"
            if not dry_run:
                try:
                    # 先複製內容到輪轉檔，再截斷原檔（保留 inode / fd）
                    shutil.copy2(fpath, rotated_path)
                    with open(fpath, "w") as f:
                        pass  # truncate in place
                except Exception as e:
                    self._results.append(RotationResult(
                        source_name=src.name, action="error",
                        file_path=fpath, detail=f"輪轉失敗: {e}",
                    ))
                    return
            self._results.append(RotationResult(
                source_name=src.name, action="truncated",
                file_path=fpath, original_size_bytes=stat.st_size,
                detail=f"超過 {src.max_size_mb} MB ({file_size_mb:.1f} MB)",
            ))
            return

    def _compress_file(self, src_path: str, gz_path: str):
        """壓縮檔案（copytruncate 語義）。
        
        流程：讀取 → 壓縮 → 截斷原檔（而非刪除）。
        這樣即使有其他行程以 >> 持有此檔的 fd，fd 不會失效，
        新資料會寫入截斷後的空檔。
        """
        stat = os.stat(src_path)
        with open(src_path, "rb") as f_in:
            with gzip.open(gz_path, "wb", compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
        # 保留時間戳
        os.utime(gz_path, (stat.st_atime, stat.st_mtime))
        # 截斷原檔（非刪除！保留 inode，不影響持有 fd 的 writer）
        with open(src_path, "w") as f:
            pass

    # ─── 空間報告 ──────────────────────────────────────────

    def get_disk_usage_report(self) -> Dict:
        """取得所有日誌來源的磁碟使用報告"""
        report = {
            "timestamp": datetime.now(TZ_GMT8).isoformat(),
            "sources": [],
            "total_bytes": 0,
            "total_files": 0,
        }

        for src in self.sources:
            files = self._resolve_files(src)
            total_size = 0
            file_count = 0
            oldest_days = 0
            for fpath in files:
                try:
                    stat = os.stat(fpath)
                    total_size += stat.st_size
                    file_count += 1
                    age = (time.time() - stat.st_mtime) / 86400
                    oldest_days = max(oldest_days, age)
                except OSError:
                    continue

            report["sources"].append({
                "name": src.name,
                "category": src.category,
                "path": src.path,
                "file_count": file_count,
                "total_bytes": total_size,
                "total_mb": round(total_size / (1024 * 1024), 2),
                "oldest_days": round(oldest_days, 1),
                "retain_days": src.retain_days,
            })
            report["total_bytes"] += total_size
            report["total_files"] += file_count

        report["total_mb"] = round(report["total_bytes"] / (1024 * 1024), 2)
        return report

    def format_report_text(self, report: Dict = None) -> str:
        """格式化磁碟使用報告為 Telegram HTML"""
        if report is None:
            report = self.get_disk_usage_report()

        lines = [
            "<b>📋 日誌治理報告</b>",
            f"{'━' * 25}",
            f"<code>時間: {report['timestamp'][:19]}</code>",
            f"<code>總檔案: {report['total_files']} 個</code>",
            f"<code>總容量: {report['total_mb']:.1f} MB</code>",
            "",
        ]

        # 按類別分組
        categories = {}
        for s in report["sources"]:
            cat = s["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(s)

        cat_icons = {
            "core": "📘", "performance": "📊", "audit": "🔒",
            "temp": "🗑️", "session": "💬", "gateway": "🌐",
        }

        for cat, sources in categories.items():
            icon = cat_icons.get(cat, "📄")
            cat_total = sum(s["total_bytes"] for s in sources)
            cat_files = sum(s["file_count"] for s in sources)
            lines.append(f"<b>{icon} {cat.upper()}</b> ({cat_files} 檔, {cat_total / 1024 / 1024:.1f} MB)")
            for s in sources:
                if s["file_count"] > 0:
                    lines.append(
                        f"  {s['name']}: {s['file_count']} 檔 "
                        f"({s['total_mb']:.1f} MB, 最舊 {s['oldest_days']:.0f}d/{s['retain_days']}d)"
                    )
            lines.append("")

        return "\n".join(lines)


# ─── 輪轉結果摘要 ─────────────────────────────────────────

def format_rotation_summary(results: List[RotationResult]) -> str:
    """輪轉結果摘要文字"""
    if not results:
        return "✅ 無需輪轉操作"

    actions = {}
    total_freed = 0
    for r in results:
        actions[r.action] = actions.get(r.action, 0) + 1
        if r.action in ("deleted", "compressed"):
            total_freed += r.original_size_bytes - r.new_size_bytes

    parts = []
    if actions.get("deleted"):
        parts.append(f"🗑️ 刪除 {actions['deleted']} 檔")
    if actions.get("compressed"):
        parts.append(f"📦 壓縮 {actions['compressed']} 檔")
    if actions.get("truncated"):
        parts.append(f"✂️ 輪轉 {actions['truncated']} 檔")
    if actions.get("error"):
        parts.append(f"❌ 錯誤 {actions['error']} 筆")

    freed_mb = total_freed / (1024 * 1024)
    summary = " | ".join(parts)
    if freed_mb > 0.01:
        summary += f"\n釋放空間: {freed_mb:.1f} MB"
    return summary


# ─── CLI 入口 ─────────────────────────────────────────────

def main():
    """獨立執行：日誌輪轉 + 報告"""
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw 日誌治理引擎")
    parser.add_argument("--dry-run", action="store_true", help="僅報告不執行")
    parser.add_argument("--report", action="store_true", help="僅輸出磁碟使用報告")
    args = parser.parse_args()

    engine = LogGovernanceEngine()

    if args.report:
        report = engine.get_disk_usage_report()
        # 輸出純文字版本
        for s in report["sources"]:
            if s["file_count"] > 0:
                print(f"  {s['name']:25s} {s['file_count']:3d} 檔  {s['total_mb']:8.2f} MB  "
                      f"(最舊 {s['oldest_days']:.0f}d / 保留 {s['retain_days']}d)")
        print(f"\n  {'合計':25s} {report['total_files']:3d} 檔  {report['total_mb']:8.2f} MB")
        return

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"{prefix}🔄 開始日誌輪轉...")
    results = engine.run_rotation(dry_run=args.dry_run)
    print(f"{prefix}{format_rotation_summary(results)}")

    for r in results:
        size_str = f"{r.original_size_bytes / 1024:.1f} KB"
        print(f"  {r.action:12s} {r.source_name:25s} {size_str:>10s}  {r.detail}")


if __name__ == "__main__":
    main()
