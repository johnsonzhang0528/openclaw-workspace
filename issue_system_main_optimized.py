#!/usr/bin/env python3
"""
智慧議題追蹤系統 - 優化版主要整合模組
整合內容優化器，降低閱讀成本
"""

import json
import os
import sys
import re
from datetime import datetime
from issue_manager import get_manager
from issue_telegram_handler_optimized import OptimizedTelegramIssueHandler
from issue_optimizer import IssueContentOptimizer

class OptimizedIssueSystem:
    def __init__(self):
        self.manager = get_manager()
        self.telegram_handler = OptimizedTelegramIssueHandler()
        self.optimizer = IssueContentOptimizer()
        
    def process_input(self, user_input: str, is_command: bool = False) -> dict:
        """
        處理使用者輸入（優化版）
        返回: {
            "response": 優化後的回覆文字,
            "buttons": 優化後的按鈕,
            "should_reply": 是否需要回覆,
            "system_notes": 系統內部註記
        }
        """
        # 檢查是否為指令
        if is_command or user_input.startswith("/"):
            return self.process_command_optimized(user_input)
        else:
            return self.process_message_optimized(user_input)
    
    def process_command_optimized(self, command: str) -> dict:
        """處理指令（優化版）"""
        # 清理指令
        clean_command = command.strip()
        
        # 處理議題相關指令
        if clean_command in ["/issue", "/issueHistory"] or clean_command.startswith("/issue_"):
            result = self.telegram_handler.handle_command(clean_command)
            
            # 進一步優化系統訊息
            if result["text"]:
                result["text"] = self.optimizer.optimize_system_message(result["text"])
            
            return {
                "response": result["text"],
                "buttons": result["buttons"],
                "should_reply": True,
                "system_notes": f"處理指令: {clean_command}"
            }
        
        # 其他指令
        return {
            "response": f"📌 指令收到",
            "buttons": [
                [{"text": "📋 議題列表", "callback_data": "/issue"}],
                [{"text": "📚 歷史議題", "callback_data": "/issueHistory"}]
            ],
            "should_reply": True,
            "system_notes": f"未知指令: {clean_command}"
        }
    
    def process_message_optimized(self, message: str) -> dict:
        """處理一般訊息（優化版）"""
        # 首先檢查是否為議題相關的特殊訊息
        if self.is_issue_related_message(message):
            return self.process_issue_related_message_optimized(message)
        
        # 正常訊息處理
        result = self.telegram_handler.process_message_optimized(message)
        
        response_parts = []
        system_notes = []
        
        if result["new_issue"]:
            response_parts.append(result["text"])
            system_notes.append(f"建立新議題: {result['issue_title']} (ID: {result['issue_id']})")
            
            # 設定為當前議題
            self.manager.set_current_issue(result["issue_id"])
            
            # 簡化詢問
            response_parts.append("\n開始討論？")
            
            return {
                "response": "\n".join(response_parts),
                "buttons": [
                    [
                        {"text": "✅ 開始", "callback_data": f"/issue_continue_{result['issue_id']}"},
                        {"text": "❌ 稍後", "callback_data": "/issue"}
                    ]
                ],
                "should_reply": True,
                "system_notes": "; ".join(system_notes)
            }
        
        elif result["issue_id"]:
            # 更新現有議題
            current_issue = self.manager.get_issue(result["issue_id"])
            if current_issue:
                system_notes.append(f"更新議題: {current_issue['title']}")
                
                # 檢查是否需要詢問關閉議題
                if self.should_ask_close_issue_optimized(message, current_issue):
                    simple_title = self.optimizer.simplify_title(current_issue["title"])
                    response_parts.append(f"📝 {simple_title}")
                    response_parts.append("\n討論完成？")
                    
                    return {
                        "response": "\n".join(response_parts),
                        "buttons": [
                            [
                                {"text": "✅ 完成", "callback_data": f"/issue_close_{result['issue_id']}"},
                                {"text": "🔁 繼續", "callback_data": f"/issue_continue_{result['issue_id']}"}
                            ]
                        ],
                        "should_reply": True,
                        "system_notes": "; ".join(system_notes)
                    }
                
                # 簡化正常回應
                simple_title = self.optimizer.simplify_title(current_issue["title"])
                return {
                    "response": f"📝 {simple_title}",
                    "buttons": [
                        [{"text": "📋 查看", "callback_data": f"/issue_view_{result['issue_id']}"}]
                    ],
                    "should_reply": True,
                    "system_notes": "; ".join(system_notes)
                }
        
        # 沒有關聯議題的一般訊息
        return {
            "response": "",
            "buttons": [],
            "should_reply": False,
            "system_notes": "一般訊息"
        }
    
    def is_issue_related_message(self, message: str) -> bool:
        """檢查是否為議題相關的特殊訊息"""
        issue_keywords = ["議題", "issue", "問題", "討論", "主題", "關閉", "結束", "解決"]
        message_lower = message.lower()
        
        for keyword in issue_keywords:
            if keyword in message_lower:
                return True
        
        return False
    
    def process_issue_related_message_optimized(self, message: str) -> dict:
        """處理議題相關的特殊訊息（優化版）"""
        message_lower = message.lower()
        
        # 檢查是否要關閉當前議題
        close_keywords = ["關閉議題", "結束討論", "解決問題", "完成議題", "好了", "完成"]
        for keyword in close_keywords:
            if keyword in message_lower:
                current_issue = self.manager.get_current_issue()
                if current_issue:
                    simple_title = self.optimizer.simplify_title(current_issue["title"])
                    return {
                        "response": f"關閉「{simple_title}」？",
                        "buttons": [
                            [
                                {"text": "✅ 關閉", "callback_data": f"/issue_close_{current_issue['id']}"},
                                {"text": "❌ 繼續", "callback_data": f"/issue_continue_{current_issue['id']}"}
                            ]
                        ],
                        "should_reply": True,
                        "system_notes": f"要求關閉議題: {current_issue['title']}"
                    }
        
        # 檢查是否要查看議題列表
        list_keywords = ["議題列表", "查看議題", "有哪些議題", "議題", "issues"]
        for keyword in list_keywords:
            if keyword in message_lower:
                return {
                    "response": "議題列表：",
                    "buttons": [[{"text": "📋 查看", "callback_data": "/issue"}]],
                    "should_reply": True,
                    "system_notes": "要求查看議題列表"
                }
        
        # 簡化預設回應
        return {
            "response": "議題操作：",
            "buttons": [
                [{"text": "📋 列表", "callback_data": "/issue"}],
                [{"text": "🆕 新建", "callback_data": "/issue_new"}],
                [{"text": "❌ 取消", "callback_data": "/issue_cancel"}]
            ],
            "should_reply": True,
            "system_notes": "議題相關詢問"
        }
    
    def should_ask_close_issue_optimized(self, message: str, issue: dict) -> bool:
        """檢查是否應該詢問關閉議題（優化版）"""
        # 更敏感的結束偵測
        end_indicators = [
            "好了", "完成", "結束", "解決", "搞定", "就這樣", "差不多了",
            "ok", "okay", "done", "finished", "完畢", "完結", "結束了"
        ]
        
        message_lower = message.lower()
        
        # 檢查是否有結束討論的明確指示
        for indicator in end_indicators:
            if indicator in message_lower:
                return True
        
        # 檢查訊息是否簡短（可能表示討論結束）
        if len(message.strip()) < 20 and any(word in message_lower for word in ["好", "行", "可", "嗯"]):
            return True
        
        # 檢查議題討論次數
        if len(issue.get("discussions", [])) >= 3:
            return True
        
        return False
    
    def get_system_status_optimized(self) -> dict:
        """取得優化後的系統狀態"""
        open_issues = self.manager.get_open_issues()
        closed_issues = self.manager.get_closed_issues()
        current_issue = self.manager.get_current_issue()
        
        status = {
            "total": len(open_issues) + len(closed_issues),
            "open": len(open_issues),
            "closed": len(closed_issues),
            "current": self.optimizer.simplify_title(current_issue["title"]) if current_issue else None,
            "auto": self.manager.index["settings"]["auto_detection"]
        }
        
        return status

# 全域實例
optimized_issue_system = None

def get_optimized_issue_system():
    """取得優化版議題系統實例"""
    global optimized_issue_system
    if optimized_issue_system is None:
        optimized_issue_system = OptimizedIssueSystem()
    return optimized_issue_system

def test_optimized_system():
    """測試優化版系統"""
    system = get_optimized_issue_system()
    
    print("=== 測試優化版議題系統 ===\n")
    
    # 測試1: 處理新主題訊息
    print("測試1: 處理新主題訊息")
    test_message1 = "我們來討論網站效能優化策略"
    result1 = system.process_input(test_message1)
    print(f"輸入: {test_message1}")
    print(f"回應: {result1['response']}")
    print(f"按鈕: {len(result1['buttons'])} 組")
    print()
    
    # 測試2: 處理指令
    print("測試2: 處理 /issue 指令")
    result2 = system.process_input("/issue", is_command=True)
    print(f"回應長度: {len(result2['response'])} 字元")
    print(f"按鈕: {len(result2['buttons'])} 組")
    print()
    
    # 測試3: 處理結束討論
    print("測試3: 處理結束討論訊息")
    test_message3 = "好的，這個議題討論完成"
    result3 = system.process_input(test_message3)
    print(f"輸入: {test_message3}")
    print(f"回應: {result3['response']}")
    print()
    
    # 測試4: 簡化詢問
    print("測試4: 簡化議題操作")
    test_message4 = "議題列表"
    result4 = system.process_input(test_message4)
    print(f"輸入: {test_message4}")
    print(f"回應: {result4['response']}")
    print(f"按鈕文字: {result4['buttons'][0][0]['text']}")
    print()
    
    # 顯示系統狀態
    status = system.get_system_status_optimized()
    print("系統狀態 (優化版):")
    print(json.dumps(status, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_optimized_system()