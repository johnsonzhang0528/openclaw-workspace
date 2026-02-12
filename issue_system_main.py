#!/usr/bin/env python3
"""
智慧議題追蹤系統 - 主要整合模組
整合到 OpenClaw 系統中
"""

import json
import os
import sys
import re
from datetime import datetime
from issue_manager import get_manager
from issue_telegram_handler import TelegramIssueHandler

class IssueSystem:
    def __init__(self):
        self.manager = get_manager()
        self.telegram_handler = TelegramIssueHandler()
        
    def process_input(self, user_input: str, is_command: bool = False) -> dict:
        """
        處理使用者輸入
        返回: {
            "response": 回覆文字,
            "buttons": inline keyboard 按鈕,
            "should_reply": 是否需要回覆,
            "system_notes": 系統內部註記
        }
        """
        # 檢查是否為指令
        if is_command or user_input.startswith("/"):
            return self.process_command(user_input)
        else:
            return self.process_message(user_input)
    
    def process_command(self, command: str) -> dict:
        """處理指令"""
        # 清理指令（移除可能的前綴）
        clean_command = command.strip()
        
        # 處理議題相關指令
        if clean_command in ["/issue", "/issueHistory"] or clean_command.startswith("/issue_"):
            result = self.telegram_handler.handle_command(clean_command)
            
            return {
                "response": result["text"],
                "buttons": result["buttons"],
                "should_reply": True,
                "system_notes": f"處理指令: {clean_command}"
            }
        
        # 其他指令
        return {
            "response": f"指令 '{clean_command}' 已收到，但議題系統不處理此指令。",
            "buttons": [],
            "should_reply": True,
            "system_notes": f"未知指令: {clean_command}"
        }
    
    def process_message(self, message: str) -> dict:
        """處理一般訊息"""
        # 首先檢查是否為議題相關的特殊訊息
        if self.is_issue_related_message(message):
            return self.process_issue_related_message(message)
        
        # 正常訊息處理
        result = self.telegram_handler.process_message(message)
        
        response_parts = []
        system_notes = []
        
        if result["new_issue"]:
            response_parts.append(result["text"])
            system_notes.append(f"建立新議題: {result['issue_title']} (ID: {result['issue_id']})")
            
            # 設定為當前議題
            self.manager.set_current_issue(result["issue_id"])
            
            # 詢問是否要開始討論
            response_parts.append("\n\n是否要開始討論這個議題？")
            
            return {
                "response": "\n".join(response_parts),
                "buttons": [
                    [
                        {"text": "✅ 開始討論", "callback_data": f"/issue_continue_{result['issue_id']}"},
                        {"text": "❌ 稍後再說", "callback_data": "/issue"}
                    ]
                ],
                "should_reply": True,
                "system_notes": "; ".join(system_notes)
            }
        
        elif result["issue_id"]:
            # 更新現有議題
            current_issue = self.manager.get_issue(result["issue_id"])
            if current_issue:
                system_notes.append(f"更新議題: {current_issue['title']} (ID: {result['issue_id']})")
                
                # 檢查是否需要詢問關閉議題
                if self.should_ask_close_issue(message, current_issue):
                    response_parts.append(f"📝 已記錄到議題: {current_issue['title']}")
                    response_parts.append("\n這個議題似乎已經討論得差不多了，是否要關閉？")
                    
                    return {
                        "response": "\n".join(response_parts),
                        "buttons": [
                            [
                                {"text": "✅ 關閉議題", "callback_data": f"/issue_close_{result['issue_id']}"},
                                {"text": "🔁 繼續討論", "callback_data": f"/issue_continue_{result['issue_id']}"}
                            ]
                        ],
                        "should_reply": True,
                        "system_notes": "; ".join(system_notes)
                    }
                
                # 正常回應
                return {
                    "response": f"📝 已記錄到議題: {current_issue['title']}",
                    "buttons": [
                        [{"text": "📋 查看議題", "callback_data": f"/issue_view_{result['issue_id']}"}]
                    ],
                    "should_reply": True,
                    "system_notes": "; ".join(system_notes)
                }
        
        # 沒有關聯議題的一般訊息
        return {
            "response": "",
            "buttons": [],
            "should_reply": False,
            "system_notes": "一般訊息，未關聯到特定議題"
        }
    
    def is_issue_related_message(self, message: str) -> bool:
        """檢查是否為議題相關的特殊訊息"""
        issue_keywords = ["議題", "issue", "問題", "討論", "主題", "關閉", "結束", "解決"]
        message_lower = message.lower()
        
        for keyword in issue_keywords:
            if keyword in message_lower:
                return True
        
        return False
    
    def process_issue_related_message(self, message: str) -> dict:
        """處理議題相關的特殊訊息"""
        message_lower = message.lower()
        
        # 檢查是否要關閉當前議題
        close_keywords = ["關閉議題", "結束討論", "解決問題", "完成議題"]
        for keyword in close_keywords:
            if keyword in message_lower:
                current_issue = self.manager.get_current_issue()
                if current_issue:
                    return {
                        "response": f"要關閉議題 '{current_issue['title']}' 嗎？",
                        "buttons": [
                            [
                                {"text": "✅ 是的，關閉", "callback_data": f"/issue_close_{current_issue['id']}"},
                                {"text": "❌ 繼續討論", "callback_data": f"/issue_continue_{current_issue['id']}"}
                            ]
                        ],
                        "should_reply": True,
                        "system_notes": f"使用者要求關閉議題: {current_issue['title']}"
                    }
        
        # 檢查是否要查看議題列表
        list_keywords = ["議題列表", "查看議題", "有哪些議題"]
        for keyword in list_keywords:
            if keyword in message_lower:
                return {
                    "response": "這是當前的議題列表：",
                    "buttons": [[{"text": "📋 查看議題列表", "callback_data": "/issue"}]],
                    "should_reply": True,
                    "system_notes": "使用者要求查看議題列表"
                }
        
        # 預設回應
        return {
            "response": "我偵測到你在討論議題相關的事情。需要我幫你：\n1. 查看當前議題列表\n2. 關閉當前議題\n3. 建立新議題嗎？",
            "buttons": [
                [{"text": "📋 議題列表", "callback_data": "/issue"}],
                [{"text": "🆕 建立新議題", "callback_data": "/issue_new"}],
                [{"text": "❌ 取消", "callback_data": "/issue_cancel"}]
            ],
            "should_reply": True,
            "system_notes": "議題相關的一般詢問"
        }
    
    def should_ask_close_issue(self, message: str, issue: dict) -> bool:
        """檢查是否應該詢問關閉議題"""
        # 檢查訊息中是否有結束討論的跡象
        end_indicators = ["好了", "完成", "結束", "解決", "搞定", "就這樣", "差不多了"]
        message_lower = message.lower()
        
        for indicator in end_indicators:
            if indicator in message_lower:
                return True
        
        # 檢查議題討論次數（如果討論超過5次，可能可以結束）
        if len(issue.get("discussions", [])) >= 5:
            return True
        
        return False
    
    def get_system_status(self) -> dict:
        """取得系統狀態"""
        open_issues = self.manager.get_open_issues()
        closed_issues = self.manager.get_closed_issues()
        current_issue = self.manager.get_current_issue()
        
        status = {
            "total_issues": len(open_issues) + len(closed_issues),
            "open_issues": len(open_issues),
            "closed_issues": len(closed_issues),
            "current_issue": current_issue["title"] if current_issue else None,
            "auto_detection": self.manager.index["settings"]["auto_detection"]
        }
        
        return status

# 全域實例
issue_system = None

def get_issue_system():
    """取得議題系統實例"""
    global issue_system
    if issue_system is None:
        issue_system = IssueSystem()
    return issue_system

def test_system():
    """測試系統功能"""
    system = get_issue_system()
    
    print("=== 測試議題系統 ===\n")
    
    # 測試1: 處理一般訊息（應該建立新議題）
    print("測試1: 處理新主題訊息")
    test_message1 = "我們來討論三個網站的GSC數據分析技能"
    result1 = system.process_message(test_message1)
    print(f"輸入: {test_message1}")
    print(f"回應: {result1['response'][:100]}...")
    print(f"需要回覆: {result1['should_reply']}")
    print()
    
    # 測試2: 處理指令
    print("測試2: 處理 /issue 指令")
    result2 = system.process_command("/issue")
    print(f"按鈕數量: {len(result2['buttons'])}")
    print()
    
    # 測試3: 處理結束討論的訊息
    print("測試3: 處理結束討論訊息")
    test_message3 = "好的，這個議題討論得差不多了"
    result3 = system.process_message(test_message3)
    print(f"輸入: {test_message3}")
    print(f"回應: {result3['response'][:100]}...")
    print()
    
    # 顯示系統狀態
    status = system.get_system_status()
    print("系統狀態:")
    print(json.dumps(status, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_system()