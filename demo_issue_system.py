#!/usr/bin/env python3
"""
智慧議題追蹤系統演示
展示系統的完整功能
"""

import json
import sys
import os
from datetime import datetime

# 添加工作空間路徑
sys.path.append('/root/.openclaw/workspace')

def demo():
    """演示系統功能"""
    print("=== 智慧議題追蹤系統演示 ===\n")
    
    # 載入系統
    from issue_integration import process_message_for_openclaw, handle_callback_query
    
    print("🎬 場景1：建立新議題")
    print("-" * 40)
    
    # 模擬使用者輸入
    messages = [
        "我們來討論三個網站的GSC數據分析技能",
        "首先，我們需要收集三個網站的GSC數據",
        "然後分析關鍵字表現和點擊率",
        "對了，關於多任務議題同步討論可行性",
        "我們需要考慮上下文切換的效能問題",
        "回到GSC分析，我覺得還需要看排名變化"
    ]
    
    for i, msg in enumerate(messages, 1):
        print(f"\n{i}. 使用者: {msg}")
        result = process_message_for_openclaw(msg)
        
        if result["text"]:
            print(f"   系統: {result['text'][:80]}...")
        
        metadata = result.get("metadata", {})
        if metadata.get("has_issue"):
            print(f"   議題: {metadata.get('issue_title')} (ID: {metadata.get('issue_id')})")
    
    print("\n" + "=" * 40)
    print("🎬 場景2：使用 /issue 指令")
    print("-" * 40)
    
    result = process_message_for_openclaw("/issue", is_command=True)
    print(f"系統回覆長度: {len(result['text'])} 字元")
    print(f"按鈕數量: {len(result['buttons'])} 組")
    
    # 顯示議題列表
    lines = result["text"].split("\n")
    for line in lines[:10]:
        if line.strip():
            print(f"   {line}")
    
    print("\n" + "=" * 40)
    print("🎬 場景3：模擬點擊議題")
    print("-" * 40)
    
    # 先取得議題列表來獲取議題ID
    from issue_system_main import get_issue_system
    system = get_issue_system()
    open_issues = system.manager.get_open_issues()
    
    if open_issues:
        issue_id = open_issues[0]["id"]
        print(f"模擬點擊議題: {open_issues[0]['title']}")
        
        # 模擬點擊
        result = handle_callback_query(f"/issue_view_{issue_id}")
        print(f"系統回覆:\n{result['text'][:200]}...")
        
        # 顯示按鈕
        print(f"\n可用操作:")
        for btn_group in result["buttons"]:
            for btn in btn_group:
                print(f"   [{btn['text']}] -> {btn['callback_data']}")
    else:
        print("目前沒有開啟的議題")
    
    print("\n" + "=" * 40)
    print("🎬 場景4：系統狀態")
    print("-" * 40)
    
    status = system.get_system_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 40)
    print("🎬 場景5：模擬關閉議題")
    print("-" * 40)
    
    if open_issues:
        issue_id = open_issues[0]["id"]
        print(f"模擬關閉議題: {open_issues[0]['title']}")
        
        result = handle_callback_query(f"/issue_close_{issue_id}")
        print(f"系統回覆:\n{result['text']}")
    
    print("\n" + "=" * 40)
    print("🎬 場景6：查看歷史議題")
    print("-" * 40)
    
    result = process_message_for_openclaw("/issueHistory", is_command=True)
    print(f"系統回覆長度: {len(result['text'])} 字元")
    
    lines = result["text"].split("\n")
    for line in lines[:8]:
        if line.strip():
            print(f"   {line}")
    
    print("\n" + "=" * 40)
    print("演示完成！")
    print("\n系統功能總結:")
    print("1. ✅ 自動議題偵測")
    print("2. ✅ 上下文自動切換")
    print("3. ✅ 互動式議題管理")
    print("4. ✅ 完整歷史記錄")
    print("5. ✅ Telegram inline keyboard 整合")

if __name__ == "__main__":
    demo()