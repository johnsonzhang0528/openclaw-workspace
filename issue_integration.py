#!/usr/bin/env python3
"""
智慧議題追蹤系統 - OpenClaw 整合模組
這個模組會被 OpenClaw 呼叫來處理訊息
"""

import json
import os
import re
import sys
from datetime import datetime

# 添加工作空間路徑到 Python 路徑
sys.path.append('/root/.openclaw/workspace')

try:
    from issue_system_main import get_issue_system
    HAS_ISSUE_SYSTEM = True
except ImportError as e:
    print(f"無法載入議題系統模組: {e}")
    HAS_ISSUE_SYSTEM = False

def process_message_for_openclaw(user_input: str, is_command: bool = False) -> dict:
    """
    為 OpenClaw 處理訊息的入口點
    返回: {
        "text": 回覆文字（如果為空則不回覆）,
        "buttons": inline keyboard 按鈕陣列,
        "metadata": 額外元資料
    }
    """
    if not HAS_ISSUE_SYSTEM:
        return {
            "text": "⚠️ 議題系統未正確載入，請檢查系統設定。",
            "buttons": [],
            "metadata": {"error": "issue_system_not_loaded"}
        }
    
    try:
        system = get_issue_system()
        result = system.process_input(user_input, is_command)
        
        # 轉換為 OpenClaw 格式
        openclaw_result = {
            "text": result["response"] if result.get("should_reply", False) else "",
            "buttons": result.get("buttons", []),
            "metadata": {
                "system_notes": result.get("system_notes", ""),
                "has_issue": result.get("issue_id") is not None,
                "issue_id": result.get("issue_id"),
                "issue_title": result.get("issue_title")
            }
        }
        
        return openclaw_result
        
    except Exception as e:
        return {
            "text": f"❌ 處理訊息時發生錯誤: {str(e)}",
            "buttons": [],
            "metadata": {"error": str(e)}
        }

def handle_callback_query(callback_data: str) -> dict:
    """
    處理 callback query（按鈕點擊）
    返回與 process_message_for_openclaw 相同的格式
    """
    if not HAS_ISSUE_SYSTEM:
        return {
            "text": "⚠️ 議題系統未正確載入",
            "buttons": [],
            "metadata": {"error": "issue_system_not_loaded"}
        }
    
    try:
        system = get_issue_system()
        
        # callback_data 就是指令
        result = system.process_command(callback_data)
        
        openclaw_result = {
            "text": result["response"],
            "buttons": result.get("buttons", []),
            "metadata": {
                "system_notes": result.get("system_notes", ""),
                "is_callback": True,
                "callback_data": callback_data
            }
        }
        
        return openclaw_result
        
    except Exception as e:
        return {
            "text": f"❌ 處理回調時發生錯誤: {str(e)}",
            "buttons": [],
            "metadata": {"error": str(e)}
        }

def get_system_status() -> dict:
    """取得系統狀態"""
    if not HAS_ISSUE_SYSTEM:
        return {"error": "議題系統未載入"}
    
    try:
        system = get_issue_system()
        return system.get_system_status()
    except Exception as e:
        return {"error": str(e)}

# 測試函數
def test_integration():
    """測試整合功能"""
    print("=== 測試 OpenClaw 整合 ===\n")
    
    if not HAS_ISSUE_SYSTEM:
        print("❌ 議題系統未載入")
        return
    
    # 測試1: 處理新議題訊息
    print("測試1: 新議題訊息")
    test_msg = "我們來討論三個網站的GSC數據分析技能"
    result1 = process_message_for_openclaw(test_msg)
    print(f"輸入: {test_msg}")
    print(f"回覆文字: {result1['text'][:50]}...")
    print(f"按鈕數量: {len(result1['buttons'])}")
    print(f"元資料: {json.dumps(result1['metadata'], ensure_ascii=False)}")
    print()
    
    # 測試2: 處理指令
    print("測試2: /issue 指令")
    result2 = process_message_for_openclaw("/issue", is_command=True)
    print(f"回覆文字長度: {len(result2['text'])}")
    print(f"按鈕數量: {len(result2['buttons'])}")
    print()
    
    # 測試3: 處理 callback
    print("測試3: callback 處理")
    result3 = handle_callback_query("/issue")
    print(f"回覆文字長度: {len(result3['text'])}")
    print(f"按鈕數量: {len(result3['buttons'])}")
    print()
    
    # 測試4: 系統狀態
    print("測試4: 系統狀態")
    status = get_system_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_integration()