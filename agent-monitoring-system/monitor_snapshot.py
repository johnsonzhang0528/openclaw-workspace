#!/usr/bin/env python3
"""
/monitor 快速回應腳本
─────────────────────
直接讀取 monitoring_state.json 並回傳已格式化的儀表板文字。
回應時間 < 50ms（無需任何系統指標採集）。

可被 OpenClaw SOUL.md skill 直接呼叫：
    python3 monitor_snapshot.py
或在程式中引用：
    from health_engine import get_monitor_snapshot_text
"""

import json
import os
import sys

STATE_FILE = "/root/.openclaw/monitoring/monitoring_state.json"

def main():
    if not os.path.exists(STATE_FILE):
        print("⚠️ 監控系統尚未執行第一次採集，請稍候 30 秒")
        return

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        print(f"❌ 讀取狀態檔案失敗: {e}")
        return

    # 使用純文字模式（html=False），因為此腳本經常由 OpenClaw AI 呼叫，
    # AI 會將輸出作為純文字傳送，不解析 HTML 標籤。
    from health_engine import render_dashboard
    print(render_dashboard(state, html=False))

if __name__ == "__main__":
    main()
