#!/usr/bin/env python3
"""
Telegram 議題追蹤系統處理器（優化版）
整合內容優化器，降低閱讀成本
"""

import json
import os
from datetime import datetime
from issue_manager import get_manager
from issue_optimizer import IssueContentOptimizer

class OptimizedTelegramIssueHandler:
    def __init__(self):
        self.manager = get_manager()
        self.optimizer = IssueContentOptimizer()
    
    def handle_command(self, command: str, message_text: str = "") -> dict:
        """
        處理指令（優化版）
        返回: {
            "text": 優化後的回覆文字,
            "buttons": 優化後的按鈕陣列,
            "edit": 是否編輯原訊息
        }
        """
        if command == "/issue":
            return self.show_issue_list_optimized()
        elif command == "/issueHistory":
            return self.show_issue_history_optimized()
        elif command.startswith("/issue_"):
            # 處理議題操作
            parts = command.split("_")
            if len(parts) >= 3:
                action = parts[1]
                issue_id = parts[2]
                
                if action == "view":
                    return self.view_issue_optimized(issue_id)
                elif action == "close":
                    return self.close_issue_optimized(issue_id)
                elif action == "reopen":
                    return self.reopen_issue_optimized(issue_id)
                elif action == "history":
                    return self.view_issue_history_optimized_detail(issue_id)
        
        return {
            "text": "❓ 未知指令",
            "buttons": [],
            "edit": False
        }
    
    def show_issue_list_optimized(self) -> dict:
        """顯示優化後的議題列表"""
        open_issues = self.manager.get_open_issues()
        
        # 使用優化器生成文字
        text = self.optimizer.optimize_issue_list(open_issues, "當前議題")
        
        # 優化按鈕
        buttons = []
        if open_issues:
            for issue in open_issues:
                simple_title = self.optimizer.simplify_title(issue["title"])
                btn_text = f"📝 {simple_title[:10]}"
                buttons.append([
                    {"text": btn_text, "callback_data": f"/issue_view_{issue['id']}"}
                ])
        
        # 操作按鈕
        buttons.append([{"text": "🔄", "callback_data": "/issue"}])
        buttons.append([
            {"text": "📚 歷史", "callback_data": "/issueHistory"},
            {"text": "🆕 新建", "callback_data": "/issue_new"}
        ])
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": False
        }
    
    def show_issue_history_optimized(self) -> dict:
        """顯示優化後的歷史議題列表"""
        closed_issues = self.manager.get_closed_issues()
        
        # 使用優化器生成文字
        text = self.optimizer.optimize_issue_history(closed_issues)
        
        # 優化按鈕
        buttons = []
        if closed_issues:
            for issue in closed_issues:
                simple_title = self.optimizer.simplify_title(issue["title"])
                btn_text = f"📖 {simple_title[:10]}"
                buttons.append([
                    {"text": btn_text, "callback_data": f"/issue_history_{issue['id']}"}
                ])
        
        # 操作按鈕
        buttons.append([{"text": "🔄", "callback_data": "/issueHistory"}])
        buttons.append([{"text": "🔙 當前", "callback_data": "/issue"}])
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": False
        }
    
    def view_issue_optimized(self, issue_id: str) -> dict:
        """查看優化後的議題詳情"""
        issue = self.manager.get_issue(issue_id)
        if not issue:
            return {
                "text": "❌ 議題不存在",
                "buttons": [[{"text": "🔙 列表", "callback_data": "/issue"}]],
                "edit": True
            }
        
        # 使用優化器生成文字
        text = self.optimizer.optimize_issue_detail(issue)
        
        # 優化按鈕
        buttons = []
        if issue["status"] == "open":
            buttons.append([
                {"text": "✅ 關閉", "callback_data": f"/issue_close_{issue_id}"},
                {"text": "📝 繼續", "callback_data": f"/issue_continue_{issue_id}"}
            ])
        else:
            buttons.append([
                {"text": "🔄 開啟", "callback_data": f"/issue_reopen_{issue_id}"},
                {"text": "📖 記錄", "callback_data": f"/issue_history_{issue_id}"}
            ])
        
        buttons.append([{"text": "🔙 列表", "callback_data": "/issue"}])
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": True
        }
    
    def view_issue_history_optimized_detail(self, issue_id: str) -> dict:
        """查看優化後的議題完整歷史"""
        issue = self.manager.get_issue(issue_id)
        if not issue:
            return {
                "text": "❌ 議題不存在",
                "buttons": [[{"text": "🔙 歷史", "callback_data": "/issueHistory"}]],
                "edit": True
            }
        
        # 使用優化器生成文字
        text = self.optimizer.optimize_full_history(issue)
        
        # 優化按鈕
        buttons = []
        if issue["status"] == "closed":
            buttons.append([{"text": "🔄 開啟", "callback_data": f"/issue_reopen_{issue_id}"}])
        
        buttons.append([{"text": "🔙 歷史", "callback_data": "/issueHistory"}])
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": True
        }
    
    def close_issue_optimized(self, issue_id: str) -> dict:
        """關閉議題（優化版）"""
        issue = self.manager.get_issue(issue_id)
        if not issue:
            return {
                "text": "❌ 議題不存在",
                "buttons": [[{"text": "🔙 列表", "callback_data": "/issue"}]],
                "edit": True
            }
        
        # 生成最終摘要
        final_summary = self.manager.generate_full_summary(issue)
        
        if self.manager.close_issue(issue_id, final_summary):
            simple_title = self.optimizer.simplify_title(issue["title"])
            text = f"✅ 已關閉: {simple_title}\n\n📋 摘要已保存"
            
            buttons = [
                [{"text": "📖 記錄", "callback_data": f"/issue_history_{issue_id}"}],
                [{"text": "📋 列表", "callback_data": "/issue"}]
            ]
        else:
            text = "❌ 關閉失敗"
            buttons = [[{"text": "🔙 返回", "callback_data": f"/issue_view_{issue_id}"}]]
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": True
        }
    
    def reopen_issue_optimized(self, issue_id: str) -> dict:
        """重新開啟議題（優化版）"""
        if self.manager.reopen_issue(issue_id):
            text = "🔄 已重新開啟\n\n可繼續討論"
            
            buttons = [
                [{"text": "📝 查看", "callback_data": f"/issue_view_{issue_id}"}],
                [{"text": "📋 列表", "callback_data": "/issue"}]
            ]
        else:
            text = "❌ 開啟失敗"
            buttons = [[{"text": "🔙 歷史", "callback_data": "/issueHistory"}]]
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": True
        }
    
    def process_message_optimized(self, message: str) -> dict:
        """
        處理一般訊息（優化版）
        返回: {
            "text": 回覆文字（可為空）,
            "new_issue": 是否建立新議題,
            "issue_id": 議題ID,
            "issue_title": 議題標題
        }
        """
        # 偵測主題轉換
        topic_changed, suggested_title = self.manager.detect_topic_change(message)
        
        result = {
            "text": "",
            "new_issue": False,
            "issue_id": None,
            "issue_title": None
        }
        
        if topic_changed and suggested_title:
            # 建立新議題
            issue_id = self.manager.create_issue(suggested_title, message)
            self.manager.set_current_issue(issue_id)
            
            simple_title = self.optimizer.simplify_title(suggested_title)
            result.update({
                "new_issue": True,
                "issue_id": issue_id,
                "issue_title": simple_title,
                "text": f"🆕 新議題: {simple_title}"
            })
        else:
            # 更新當前議題
            current_issue = self.manager.get_current_issue()
            if current_issue:
                # 生成摘要
                summary = self.manager.generate_summary(message)
                self.manager.update_issue(current_issue["id"], message, summary)
                
                result.update({
                    "issue_id": current_issue["id"],
                    "issue_title": self.optimizer.simplify_title(current_issue["title"])
                })
        
        return result

# 測試函數
def test_optimized_handler():
    """測試優化版處理器"""
    print("=== 測試優化版議題處理器 ===\n")
    
    handler = OptimizedTelegramIssueHandler()
    
    # 先建立一些測試議題
    mgr = get_manager()
    
    # 清理現有議題
    for issue in mgr.get_open_issues():
        mgr.close_issue(issue["id"], "測試清理")
    
    # 建立測試議題
    issue1_id = mgr.create_issue("三個網站的GSC數據分析技能", "測試討論內容1")
    mgr.update_issue(issue1_id, "需要分析關鍵字表現", "關鍵字分析")
    
    issue2_id = mgr.create_issue("多任務議題同步討論可行性", "測試討論內容2")
    mgr.update_issue(issue2_id, "上下文切換效能問題", "效能考量")
    
    print("1. 測試 /issue 指令:")
    result = handler.handle_command("/issue")
    print(f"回覆文字:\n{result['text']}")
    print(f"按鈕數量: {len(result['buttons'])}")
    print()
    
    print("2. 測試議題詳情:")
    result = handler.handle_command(f"/issue_view_{issue1_id}")
    print(f"回覆文字:\n{result['text']}")
    print()
    
    print("3. 測試關閉議題:")
    result = handler.handle_command(f"/issue_close_{issue1_id}")
    print(f"回覆文字:\n{result['text']}")
    print()
    
    print("4. 測試 /issueHistory 指令:")
    result = handler.handle_command("/issueHistory")
    print(f"回覆文字:\n{result['text']}")
    print()
    
    print("5. 測試訊息處理:")
    test_msg = "我們來討論新的主題：AI輔助決策系統"
    result = handler.process_message_optimized(test_msg)
    print(f"輸入: {test_msg}")
    print(f"回覆: {result['text']}")
    print(f"新議題: {result['new_issue']}")
    print(f"議題標題: {result['issue_title']}")

if __name__ == "__main__":
    test_optimized_handler()