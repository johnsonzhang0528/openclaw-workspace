#!/usr/bin/env python3
"""
Telegram 議題追蹤系統處理器
處理 inline keyboard 互動和指令回應
"""

import json
import os
from datetime import datetime
from issue_manager import get_manager

class TelegramIssueHandler:
    def __init__(self):
        self.manager = get_manager()
    
    def handle_command(self, command: str, message_text: str = "") -> dict:
        """
        處理指令
        返回: {
            "text": 回覆文字,
            "buttons": inline keyboard 按鈕陣列,
            "edit": 是否編輯原訊息
        }
        """
        if command == "/issue":
            return self.show_issue_list()
        elif command == "/issueHistory":
            return self.show_issue_history()
        elif command.startswith("/issue_"):
            # 處理議題操作
            parts = command.split("_")
            if len(parts) >= 3:
                action = parts[1]
                issue_id = parts[2]
                
                if action == "view":
                    return self.view_issue(issue_id)
                elif action == "close":
                    return self.close_issue(issue_id)
                elif action == "reopen":
                    return self.reopen_issue(issue_id)
                elif action == "history":
                    return self.view_issue_history(issue_id)
        
        return {
            "text": "未知指令",
            "buttons": [],
            "edit": False
        }
    
    def show_issue_list(self) -> dict:
        """顯示開啟的議題列表"""
        open_issues = self.manager.get_open_issues()
        
        if not open_issues:
            text = "📋 *當前議題列表*\n\n目前沒有開啟的議題。"
            buttons = [
                [{"text": "🔄 重新整理", "callback_data": "/issue"}]
            ]
        else:
            text = "📋 *當前議題列表*\n\n"
            for i, issue in enumerate(open_issues, 1):
                created = datetime.fromisoformat(issue["created_at"]).strftime("%m/%d %H:%M")
                text += f"{i}. {issue['title']}\n   📅 建立時間: {created}\n\n"
            
            text += "點擊議題查看最後討論重點提要："
            
            # 建立按鈕
            buttons = []
            for issue in open_issues:
                buttons.append([
                    {"text": f"📝 {issue['title'][:20]}", "callback_data": f"/issue_view_{issue['id']}"}
                ])
            
            buttons.append([{"text": "🔄 重新整理", "callback_data": "/issue"}])
        
        buttons.append([{"text": "📚 查看歷史議題", "callback_data": "/issueHistory"}])
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": False
        }
    
    def show_issue_history(self) -> dict:
        """顯示已關閉的議題列表"""
        closed_issues = self.manager.get_closed_issues()
        
        if not closed_issues:
            text = "📚 *議題歷史記錄*\n\n目前沒有已關閉的議題。"
            buttons = [
                [{"text": "🔄 重新整理", "callback_data": "/issueHistory"}]
            ]
        else:
            text = "📚 *議題歷史記錄*\n\n"
            for i, issue in enumerate(closed_issues, 1):
                created = datetime.fromisoformat(issue["created_at"]).strftime("%m/%d")
                updated = datetime.fromisoformat(issue["updated_at"]).strftime("%m/%d")
                text += f"{i}. {issue['title']}\n   📅 建立: {created} | 關閉: {updated}\n\n"
            
            text += "點擊議題查看完整討論記錄："
            
            # 建立按鈕
            buttons = []
            for issue in closed_issues:
                buttons.append([
                    {"text": f"📖 {issue['title'][:20]}", "callback_data": f"/issue_history_{issue['id']}"}
                ])
            
            buttons.append([{"text": "🔄 重新整理", "callback_data": "/issueHistory"}])
        
        buttons.append([{"text": "📋 返回當前議題", "callback_data": "/issue"}])
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": False
        }
    
    def view_issue(self, issue_id: str) -> dict:
        """查看議題詳細資訊"""
        issue = self.manager.get_issue(issue_id)
        if not issue:
            return {
                "text": "❌ 找不到指定的議題",
                "buttons": [[{"text": "🔙 返回列表", "callback_data": "/issue"}]],
                "edit": True
            }
        
        created = datetime.fromisoformat(issue["created_at"]).strftime("%Y/%m/%d %H:%M")
        updated = datetime.fromisoformat(issue["updated_at"]).strftime("%Y/%m/%d %H:%M")
        status_emoji = "🟢" if issue["status"] == "open" else "🔴"
        
        text = f"📝 *{issue['title']}*\n\n"
        text += f"{status_emoji} 狀態: {'開啟' if issue['status'] == 'open' else '已關閉'}\n"
        text += f"📅 建立時間: {created}\n"
        text += f"🔄 最後更新: {updated}\n\n"
        text += "📌 *最後討論重點提要:*\n"
        text += f"{issue['last_discussion']}\n\n"
        text += f"💬 討論次數: {len(issue['discussions'])}"
        
        # 操作按鈕
        buttons = []
        if issue["status"] == "open":
            buttons.append([
                {"text": "✅ 關閉議題", "callback_data": f"/issue_close_{issue_id}"},
                {"text": "📝 繼續討論", "callback_data": f"/issue_continue_{issue_id}"}
            ])
        else:
            buttons.append([
                {"text": "🔄 重新開啟", "callback_data": f"/issue_reopen_{issue_id}"},
                {"text": "📖 查看完整記錄", "callback_data": f"/issue_history_{issue_id}"}
            ])
        
        buttons.append([{"text": "🔙 返回列表", "callback_data": "/issue"}])
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": True
        }
    
    def view_issue_history(self, issue_id: str) -> dict:
        """查看議題完整歷史記錄"""
        issue = self.manager.get_issue(issue_id)
        if not issue:
            return {
                "text": "❌ 找不到指定的議題",
                "buttons": [[{"text": "🔙 返回列表", "callback_data": "/issueHistory"}]],
                "edit": True
            }
        
        created = datetime.fromisoformat(issue["created_at"]).strftime("%Y/%m/%d %H:%M")
        updated = datetime.fromisoformat(issue["updated_at"]).strftime("%Y/%m/%d %H:%M")
        
        text = f"📖 *{issue['title']} - 完整討論記錄*\n\n"
        text += f"📅 建立時間: {created}\n"
        text += f"🔄 最後更新: {updated}\n"
        text += f"📊 狀態: {'開啟' if issue['status'] == 'open' else '已關閉'}\n\n"
        
        if issue.get("full_summary"):
            text += "📋 *完整摘要:*\n"
            text += f"{issue['full_summary']}\n\n"
        
        text += "💬 *討論記錄:*\n"
        
        discussions = issue.get("discussions", [])
        if discussions:
            for i, discussion in enumerate(discussions, 1):
                time = datetime.fromisoformat(discussion["timestamp"]).strftime("%m/%d %H:%M")
                text += f"\n{i}. [{time}] {discussion['summary']}"
        else:
            text += "\n無討論記錄"
        
        # 操作按鈕
        buttons = []
        if issue["status"] == "closed":
            buttons.append([{"text": "🔄 重新開啟", "callback_data": f"/issue_reopen_{issue_id}"}])
        
        buttons.append([{"text": "🔙 返回歷史列表", "callback_data": "/issueHistory"}])
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": True
        }
    
    def close_issue(self, issue_id: str) -> dict:
        """關閉議題"""
        issue = self.manager.get_issue(issue_id)
        if not issue:
            return {
                "text": "❌ 找不到指定的議題",
                "buttons": [[{"text": "🔙 返回列表", "callback_data": "/issue"}]],
                "edit": True
            }
        
        # 生成最終摘要
        final_summary = self.manager.generate_full_summary(issue)
        
        if self.manager.close_issue(issue_id, final_summary):
            text = f"✅ *議題已關閉*\n\n"
            text += f"📝 {issue['title']}\n\n"
            text += f"📋 最終摘要已生成，可透過 /issueHistory 查看完整記錄。"
            
            buttons = [
                [{"text": "📖 查看完整記錄", "callback_data": f"/issue_history_{issue_id}"}],
                [{"text": "📋 返回議題列表", "callback_data": "/issue"}]
            ]
        else:
            text = "❌ 關閉議題時發生錯誤"
            buttons = [[{"text": "🔙 返回", "callback_data": f"/issue_view_{issue_id}"}]]
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": True
        }
    
    def reopen_issue(self, issue_id: str) -> dict:
        """重新開啟議題"""
        if self.manager.reopen_issue(issue_id):
            text = "🔄 *議題已重新開啟*\n\n議題已恢復為開啟狀態，可以繼續討論。"
            
            buttons = [
                [{"text": "📝 查看議題", "callback_data": f"/issue_view_{issue_id}"}],
                [{"text": "📋 返回列表", "callback_data": "/issue"}]
            ]
        else:
            text = "❌ 重新開啟議題時發生錯誤"
            buttons = [[{"text": "🔙 返回", "callback_data": "/issueHistory"}]]
        
        return {
            "text": text,
            "buttons": buttons,
            "edit": True
        }
    
    def process_message(self, message: str) -> dict:
        """
        處理一般訊息，自動偵測議題
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
            
            result.update({
                "new_issue": True,
                "issue_id": issue_id,
                "issue_title": suggested_title,
                "text": f"🔍 *偵測到新議題*\n\n已建立新議題: {suggested_title}\n議題ID: {issue_id}"
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
                    "issue_title": current_issue["title"]
                })
        
        return result

# 測試程式碼
if __name__ == "__main__":
    handler = TelegramIssueHandler()
    
    # 測試指令處理
    print("測試 /issue 指令:")
    result = handler.handle_command("/issue")
    print(f"回覆文字長度: {len(result['text'])}")
    print(f"按鈕數量: {len(result['buttons'])}")
    
    print("\n測試訊息處理:")
    test_messages = [
        "我們來討論網站SEO優化策略",
        "關於資料庫設計的索引優化問題",
        "網站速度優化的幾個關鍵點"
    ]
    
    for msg in test_messages:
        result = handler.process_message(msg)
        print(f"\n訊息: {msg}")
        print(f"新議題: {result['new_issue']}")
        print(f"議題標題: {result['issue_title']}")