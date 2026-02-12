#!/usr/bin/env python3
"""
議題系統 Telegram 整合模組
提供完整的 Telegram 互動介面，包括：
1. /issue 指令處理器
2. inline keyboard 管理
3. 議題狀態切換功能
符合 MEMORY.md 中的議題系統規則
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# 添加工作空間路徑
sys.path.append('/root/.openclaw/workspace')

try:
    from issue_system_main import get_issue_system
    HAS_ISSUE_SYSTEM = True
except ImportError as e:
    print(f"無法載入議題系統模組: {e}")
    HAS_ISSUE_SYSTEM = False

class IssueTelegramIntegration:
    """議題系統 Telegram 整合類別"""
    
    def __init__(self):
        if not HAS_ISSUE_SYSTEM:
            raise ImportError("議題系統模組未正確載入")
        
        self.system = get_issue_system()
        
    def handle_telegram_command(self, command: str, args: List[str] = None) -> Dict[str, Any]:
        """
        處理 Telegram 命令
        返回格式: {
            "text": 回覆文字,
            "buttons": inline keyboard 按鈕陣列,
            "parse_mode": "Markdown" (可選),
            "edit": True/False (是否編輯原訊息)
        }
        """
        if args is None:
            args = []
        
        # 清理命令
        clean_command = command.strip().lower()
        
        # 處理議題相關命令
        if clean_command == "/issue":
            return self.handle_issue_list()
        elif clean_command == "/issuehistory":
            return self.handle_issue_history()
        elif clean_command.startswith("/issue_"):
            return self.handle_issue_action(clean_command)
        else:
            return {
                "text": "❓ 未知指令。可用指令：\n/issue - 查看當前議題列表\n/issueHistory - 查看歷史議題",
                "buttons": [],
                "parse_mode": "Markdown"
            }
    
    def handle_issue_list(self) -> Dict[str, Any]:
        """處理 /issue 指令 - 顯示當前議題列表"""
        try:
            # 使用議題系統處理指令
            result = self.system.process_command("/issue")
            
            # 優化回應文字（符合閱讀成本優化規則）
            text = self.optimize_response_text(result["response"])
            
            return {
                "text": text,
                "buttons": result["buttons"],
                "parse_mode": "Markdown",
                "edit": False
            }
        except Exception as e:
            return {
                "text": f"❌ 處理議題列表時發生錯誤：{str(e)}",
                "buttons": [],
                "parse_mode": "Markdown"
            }
    
    def handle_issue_history(self) -> Dict[str, Any]:
        """處理 /issueHistory 指令 - 顯示歷史議題"""
        try:
            result = self.system.process_command("/issueHistory")
            
            # 優化回應文字
            text = self.optimize_response_text(result["response"])
            
            return {
                "text": text,
                "buttons": result["buttons"],
                "parse_mode": "Markdown",
                "edit": False
            }
        except Exception as e:
            return {
                "text": f"❌ 處理議題歷史時發生錯誤：{str(e)}",
                "buttons": [],
                "parse_mode": "Markdown"
            }
    
    def handle_issue_action(self, command: str) -> Dict[str, Any]:
        """處理議題操作命令（如 /issue_view_xxx, /issue_close_xxx 等）"""
        try:
            # 直接使用議題系統處理 callback
            result = self.system.process_command(command)
            
            # 優化回應文字
            text = self.optimize_response_text(result["response"])
            
            return {
                "text": text,
                "buttons": result["buttons"],
                "parse_mode": "Markdown",
                "edit": True  # 議題操作通常需要編輯原訊息
            }
        except Exception as e:
            return {
                "text": f"❌ 處理議題操作時發生錯誤：{str(e)}",
                "buttons": [],
                "parse_mode": "Markdown",
                "edit": True
            }
    
    def handle_callback_query(self, callback_data: str) -> Dict[str, Any]:
        """
        處理 Telegram callback query（按鈕點擊）
        返回格式與 handle_telegram_command 相同
        """
        try:
            # 使用議題系統處理 callback
            result = self.system.process_command(callback_data)
            
            # 優化回應文字
            text = self.optimize_response_text(result["response"])
            
            return {
                "text": text,
                "buttons": result["buttons"],
                "parse_mode": "Markdown",
                "edit": True  # callback 通常需要編輯原訊息
            }
        except Exception as e:
            return {
                "text": f"❌ 處理按鈕點擊時發生錯誤：{str(e)}",
                "buttons": [],
                "parse_mode": "Markdown",
                "edit": True
            }
    
    def process_message_for_telegram(self, message: str) -> Dict[str, Any]:
        """
        處理一般訊息，自動偵測議題
        返回格式與 handle_telegram_command 相同
        """
        try:
            # 使用議題系統處理訊息
            result = self.system.process_input(message, is_command=False)
            
            if not result["should_reply"]:
                return {
                    "text": "",  # 空文字表示不需要回覆
                    "buttons": [],
                    "parse_mode": "Markdown"
                }
            
            # 優化回應文字
            text = self.optimize_response_text(result["response"])
            
            return {
                "text": text,
                "buttons": result["buttons"],
                "parse_mode": "Markdown",
                "edit": False
            }
        except Exception as e:
            return {
                "text": f"❌ 處理訊息時發生錯誤：{str(e)}",
                "buttons": [],
                "parse_mode": "Markdown"
            }
    
    def optimize_response_text(self, text: str) -> str:
        """
        優化回應文字，符合 MEMORY.md 中的閱讀成本優化規則：
        1. 移除冗餘文字
        2. 使用符號和格式快速傳達資訊
        3. 關鍵資訊前置
        4. 使用相對時間顯示
        5. 標題簡化
        """
        if not text:
            return text
        
        # 簡化系統訊息
        simplifications = {
            "偵測到新議題": "🔍 新議題",
            "已建立新議題": "✅ 已建立",
            "議題列表": "📋 議題",
            "議題歷史記錄": "📚 歷史",
            "最後討論重點提要": "📌 最後討論",
            "完整討論記錄": "📖 完整記錄",
            "建立時間": "📅 建立",
            "最後更新": "🔄 更新",
            "目前沒有開啟的議題": "📭 無議題",
            "目前沒有已關閉的議題": "📭 無歷史",
            "要關閉議題": "❓ 關閉議題？",
            "是否要開始討論這個議題": "❓ 開始討論？",
            "這個議題似乎已經討論得差不多了": "💭 討論完成？",
            "是否要關閉": "❓ 關閉？"
        }
        
        optimized_text = text
        for old, new in simplifications.items():
            optimized_text = optimized_text.replace(old, new)
        
        # 簡化時間顯示
        import re
        time_patterns = [
            (r'(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2})', self._simplify_time),
            (r'(\d{2})/(\d{2}) (\d{2}):(\d{2})', self._simplify_short_time),
        ]
        
        for pattern, repl_func in time_patterns:
            optimized_text = re.sub(pattern, repl_func, optimized_text)
        
        # 移除多餘的空行
        optimized_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', optimized_text)
        
        return optimized_text
    
    def _simplify_time(self, match) -> str:
        """簡化時間顯示"""
        year, month, day, hour, minute = match.groups()
        now = datetime.now()
        date_obj = datetime(int(year), int(month), int(day), int(hour), int(minute))
        
        # 計算相對時間
        delta = now - date_obj
        
        if delta.days == 0:
            if delta.seconds < 3600:  # 1小時內
                minutes = delta.seconds // 60
                return f"{minutes}m前"
            else:
                hours = delta.seconds // 3600
                return f"{hours}h前"
        elif delta.days == 1:
            return "昨天"
        elif delta.days < 7:
            return f"{delta.days}d前"
        else:
            return f"{month}/{day}"
    
    def _simplify_short_time(self, match) -> str:
        """簡化短時間顯示"""
        month, day, hour, minute = match.groups()
        return f"{month}/{day} {hour}:{minute}"
    
    def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態"""
        try:
            status = self.system.get_system_status()
            return {
                "status": "正常",
                "data": status
            }
        except Exception as e:
            return {
                "status": "錯誤",
                "error": str(e)
            }


# 全域實例
telegram_integration = None

def get_telegram_integration():
    """取得 Telegram 整合實例"""
    global telegram_integration
    if telegram_integration is None:
        telegram_integration = IssueTelegramIntegration()
    return telegram_integration


def test_telegram_integration():
    """測試 Telegram 整合功能"""
    print("=== 測試 Telegram 議題整合 ===\n")
    
    try:
        integration = get_telegram_integration()
        
        # 測試1: /issue 指令
        print("測試1: /issue 指令")
        result1 = integration.handle_telegram_command("/issue")
        print(f"回覆文字長度: {len(result1['text'])}")
        print(f"按鈕數量: {len(result1['buttons'])}")
        print(f"優化前後對比示例:")
        print(f"原始: '議題列表' -> 優化: '📋 議題'")
        print()
        
        # 測試2: /issueHistory 指令
        print("測試2: /issueHistory 指令")
        result2 = integration.handle_telegram_command("/issueHistory")
        print(f"回覆文字長度: {len(result2['text'])}")
        print(f"按鈕數量: {len(result2['buttons'])}")
        print()
        
        # 測試3: callback 處理
        print("測試3: callback 處理")
        # 先獲取一個議題ID
        system = get_issue_system()
        status = system.get_system_status()
        if status.get("open_issues", 0) > 0:
            open_issues = system.manager.get_open_issues()
            if open_issues:
                issue_id = open_issues[0]["id"]
                callback_data = f"/issue_view_{issue_id}"
                result3 = integration.handle_callback_query(callback_data)
                print(f"處理 callback: {callback_data}")
                print(f"回覆文字長度: {len(result3['text'])}")
                print(f"按鈕數量: {len(result3['buttons'])}")
                print(f"需要編輯: {result3.get('edit', False)}")
        print()
        
        # 測試4: 訊息處理
        print("測試4: 一般訊息處理")
        test_message = "我們來討論網站SEO優化策略"
        result4 = integration.process_message_for_telegram(test_message)
        print(f"輸入: {test_message}")
        print(f"需要回覆: {bool(result4['text'])}")
        if result4['text']:
            print(f"回覆文字: {result4['text'][:100]}...")
            print(f"按鈕數量: {len(result4['buttons'])}")
        print()
        
        # 測試5: 系統狀態
        print("測試5: 系統狀態")
        status_result = integration.get_system_status()
        print(f"狀態: {status_result['status']}")
        if status_result['status'] == '正常':
            print(f"議題數量: {status_result['data'].get('total_issues', 0)}")
            print(f"開啟議題: {status_result['data'].get('open_issues', 0)}")
            print(f"關閉議題: {status_result['data'].get('closed_issues', 0)}")
        
        print("\n✅ Telegram 整合測試完成")
        
    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")


if __name__ == "__main__":
    test_telegram_integration()