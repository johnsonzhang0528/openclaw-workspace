#!/usr/bin/env python3
"""
智慧議題追蹤系統 - 優化版 OpenClaw 整合模組
整合內容優化器，降低閱讀成本
"""

import json
import os
import sys

# 添加工作空間路徑到 Python 路徑
sys.path.append('/root/.openclaw/workspace')

try:
    from issue_system_main_optimized import get_optimized_issue_system
    HAS_OPTIMIZED_SYSTEM = True
except ImportError as e:
    print(f"無法載入優化版議題系統模組: {e}")
    HAS_OPTIMIZED_SYSTEM = False

def process_message_optimized(user_input: str, is_command: bool = False) -> dict:
    """
    為 OpenClaw 處理訊息的優化版入口點
    返回: {
        "text": 優化後的回覆文字（如果為空則不回覆）,
        "buttons": 優化後的 inline keyboard 按鈕陣列,
        "metadata": 額外元資料
    }
    """
    if not HAS_OPTIMIZED_SYSTEM:
        return {
            "text": "⚠️ 優化版議題系統未載入",
            "buttons": [],
            "metadata": {"error": "optimized_system_not_loaded"}
        }
    
    try:
        system = get_optimized_issue_system()
        result = system.process_input(user_input, is_command)
        
        # 轉換為 OpenClaw 格式
        openclaw_result = {
            "text": result["response"] if result.get("should_reply", False) else "",
            "buttons": result.get("buttons", []),
            "metadata": {
                "system_notes": result.get("system_notes", ""),
                "optimized": True,
                "has_issue": "issue_id" in result and result["issue_id"] is not None
            }
        }
        
        # 如果沒有文字但有按鈕，添加簡短提示
        if not openclaw_result["text"] and openclaw_result["buttons"]:
            openclaw_result["text"] = "📌"
        
        return openclaw_result
        
    except Exception as e:
        return {
            "text": f"❌ 錯誤: {str(e)[:50]}",
            "buttons": [],
            "metadata": {"error": str(e)}
        }

def handle_callback_query_optimized(callback_data: str) -> dict:
    """
    處理 callback query（按鈕點擊）優化版
    返回與 process_message_optimized 相同的格式
    """
    if not HAS_OPTIMIZED_SYSTEM:
        return {
            "text": "⚠️ 優化版系統未載入",
            "buttons": [],
            "metadata": {"error": "optimized_system_not_loaded"}
        }
    
    try:
        system = get_optimized_issue_system()
        
        # callback_data 就是指令
        result = system.process_input(callback_data, is_command=True)
        
        openclaw_result = {
            "text": result["response"],
            "buttons": result.get("buttons", []),
            "metadata": {
                "system_notes": result.get("system_notes", ""),
                "optimized": True,
                "is_callback": True,
                "callback_data": callback_data
            }
        }
        
        return openclaw_result
        
    except Exception as e:
        return {
            "text": f"❌ 錯誤: {str(e)[:50]}",
            "buttons": [],
            "metadata": {"error": str(e)}
        }

def get_system_status_optimized() -> dict:
    """取得優化版系統狀態"""
    if not HAS_OPTIMIZED_SYSTEM:
        return {"error": "優化版議題系統未載入"}
    
    try:
        system = get_optimized_issue_system()
        return system.get_system_status_optimized()
    except Exception as e:
        return {"error": str(e)}

# 測試函數
def test_optimized_integration():
    """測試優化版整合功能"""
    print("=== 測試優化版 OpenClaw 整合 ===\n")
    
    if not HAS_OPTIMIZED_SYSTEM:
        print("❌ 優化版議題系統未載入")
        return
    
    # 測試1: 處理新議題訊息
    print("測試1: 新議題訊息")
    test_msg = "討論資料庫索引優化方案"
    result1 = process_message_optimized(test_msg)
    print(f"輸入: {test_msg}")
    print(f"回覆文字: {result1['text']}")
    print(f"按鈕數量: {len(result1['buttons'])}")
    print(f"元資料: {json.dumps(result1['metadata'], ensure_ascii=False)}")
    print()
    
    # 測試2: 處理指令
    print("測試2: /issue 指令")
    result2 = process_message_optimized("/issue", is_command=True)
    print(f"回覆文字長度: {len(result2['text'])} 字元")
    print(f"按鈕數量: {len(result2['buttons'])} 組")
    
    # 顯示部分內容
    if result2['text']:
        lines = result2['text'].split('\n')
        for line in lines[:3]:
            print(f"   {line}")
    print()
    
    # 測試3: 處理 callback
    print("測試3: callback 處理")
    result3 = handle_callback_query_optimized("/issue")
    print(f"回覆文字長度: {len(result3['text'])} 字元")
    print(f"按鈕數量: {len(result3['buttons'])} 組")
    print()
    
    # 測試4: 系統狀態
    print("測試4: 系統狀態")
    status = get_system_status_optimized()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    print()
    
    # 測試5: 簡短回應
    print("測試5: 簡短操作")
    test_msg5 = "關閉議題"
    result5 = process_message_optimized(test_msg5)
    print(f"輸入: {test_msg5}")
    print(f"回覆: {result5['text']}")
    print(f"按鈕: {result5['buttons'][0][0]['text'] if result5['buttons'] else '無'}")

if __name__ == "__main__":
    test_optimized_integration()