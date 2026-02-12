#!/usr/bin/env python3
"""
全域優化中間件
整合到 OpenClaw 系統中，優化所有回覆內容
"""

import json
import sys
import os
from typing import Dict, List, Optional, Any

# 添加工作空間路徑
sys.path.append('/root/.openclaw/workspace')

try:
    from global_response_optimizer import GlobalResponseOptimizer
    HAS_GLOBAL_OPTIMIZER = True
except ImportError as e:
    print(f"無法載入全域優化器: {e}")
    HAS_GLOBAL_OPTIMIZER = False

class GlobalOptimizationMiddleware:
    """全域優化中間件"""
    
    def __init__(self):
        self.optimizer = GlobalResponseOptimizer() if HAS_GLOBAL_OPTIMIZER else None
        self.conversation_context = []
        self.max_context_length = 10
        
    def process_response(self, response: Dict, user_input: str = "") -> Dict:
        """
        處理回覆內容，進行全域優化
        Args:
            response: 原始回覆字典，包含 text 和 buttons
            user_input: 使用者輸入（用於上下文理解）
        Returns:
            優化後的回覆字典
        """
        if not self.optimizer:
            return response
        
        # 更新對話上下文
        self.update_context(user_input, response)
        
        # 優化文字內容
        if "text" in response and response["text"]:
            context_str = self.get_context_string()
            optimized_text = self.optimizer.optimize_response(response["text"], context_str)
            response["text"] = optimized_text
        
        # 優化按鈕文字（如果有的話）
        if "buttons" in response and response["buttons"]:
            response["buttons"] = self.optimize_buttons(response["buttons"])
        
        # 添加優化標記
        if "metadata" not in response:
            response["metadata"] = {}
        response["metadata"]["globally_optimized"] = True
        
        return response
    
    def update_context(self, user_input: str, assistant_response: Dict):
        """更新對話上下文"""
        # 添加使用者輸入
        if user_input:
            self.conversation_context.append({
                "role": "user",
                "content": user_input[:100]  # 限制長度
            })
        
        # 添加助手回覆
        if "text" in assistant_response and assistant_response["text"]:
            self.conversation_context.append({
                "role": "assistant",
                "content": assistant_response["text"][:100]  # 限制長度
            })
        
        # 保持上下文長度
        if len(self.conversation_context) > self.max_context_length:
            self.conversation_context = self.conversation_context[-self.max_context_length:]
    
    def get_context_string(self) -> str:
        """取得上下文字串"""
        if not self.conversation_context:
            return ""
        
        # 取最近幾條訊息
        recent_messages = self.conversation_context[-3:]  # 最近3條
        context_parts = []
        
        for msg in recent_messages:
            role = "使用者" if msg["role"] == "user" else "助手"
            context_parts.append(f"{role}: {msg['content']}")
        
        return " | ".join(context_parts)
    
    def optimize_buttons(self, buttons: List[List[Dict]]) -> List[List[Dict]]:
        """優化按鈕文字"""
        if not buttons:
            return buttons
        
        optimized_buttons = []
        
        for button_group in buttons:
            optimized_group = []
            for button in button_group:
                if "text" in button:
                    # 簡化按鈕文字
                    original_text = button["text"]
                    optimized_text = self.simplify_button_text(original_text)
                    
                    optimized_button = button.copy()
                    optimized_button["text"] = optimized_text
                    optimized_group.append(optimized_button)
                else:
                    optimized_group.append(button)
            
            optimized_buttons.append(optimized_group)
        
        return optimized_buttons
    
    def simplify_button_text(self, text: str) -> str:
        """簡化按鈕文字"""
        # 移除冗詞
        simplifications = {
            "重新整理": "🔄",
            "查看詳情": "👀",
            "開始討論": "▶️",
            "關閉議題": "✅",
            "繼續討論": "🔁",
            "返回列表": "🔙",
            "建立新議題": "🆕",
            "查看歷史": "📚",
            "確認": "✓",
            "取消": "✗",
            "是": "✅",
            "否": "❌",
            "好的": "👌",
            "明白了": "💡"
        }
        
        # 檢查完全匹配
        for original, simplified in simplifications.items():
            if text == original:
                return simplified
        
        # 檢查部分匹配
        for original, simplified in simplifications.items():
            if original in text:
                # 保留原文字但替換關鍵部分
                return text.replace(original, simplified)
        
        # 如果文字太長，截斷
        if len(text) > 15:
            return text[:12] + "..."
        
        return text
    
    def process_batch_responses(self, responses: List[Dict]) -> List[Dict]:
        """批量處理回覆"""
        if not self.optimizer:
            return responses
        
        optimized_responses = []
        
        for response in responses:
            optimized = self.process_response(response)
            optimized_responses.append(optimized)
        
        return optimized_responses

# 全域實例
global_middleware = None

def get_global_middleware():
    """取得全域優化中間件實例"""
    global global_middleware
    if global_middleware is None:
        global_middleware = GlobalOptimizationMiddleware()
    return global_middleware

def optimize_response_for_openclaw(response_data: Dict, user_input: str = "") -> Dict:
    """
    OpenClaw 整合函數：優化回覆內容
    """
    middleware = get_global_middleware()
    return middleware.process_response(response_data, user_input)

# 測試函數
def test_global_middleware():
    """測試全域優化中間件"""
    print("=== 測試全域優化中間件 ===\n")
    
    middleware = get_global_middleware()
    
    # 測試案例
    test_cases = [
        {
            "name": "一般問候回覆",
            "user_input": "你好",
            "response": {
                "text": "你好！我是你的 AI 助手，剛剛重新啟動了。今天想讓我幫你做什麼呢？",
                "buttons": []
            }
        },
        {
            "name": "技術解釋回覆",
            "user_input": "解釋議題系統",
            "response": {
                "text": "這是一個智慧型的議題追蹤系統，能夠自動偵測新議題並建立 issue 列表。系統會監聽對話內容，計算相似度，在主題轉換時建立新議題。",
                "buttons": [
                    [{"text": "查看議題列表", "callback_data": "/issue"}],
                    [{"text": "查看歷史議題", "callback_data": "/issueHistory"}]
                ]
            }
        },
        {
            "name": "錯誤回覆",
            "user_input": "執行某個功能",
            "response": {
                "text": "抱歉，執行時發生錯誤：無法載入所需模組，請檢查系統設定。",
                "buttons": [
                    [{"text": "重新嘗試", "callback_data": "/retry"}],
                    [{"text": "取消操作", "callback_data": "/cancel"}]
                ]
            }
        },
        {
            "name": "成功確認回覆",
            "user_input": "設定完成",
            "response": {
                "text": "好的，已經成功完成設定！系統現在可以正常運作了。",
                "buttons": [
                    [{"text": "確認", "callback_data": "/confirm"}],
                    [{"text": "測試功能", "callback_data": "/test"}]
                ]
            }
        }
    ]
    
    for test in test_cases:
        print(f"測試: {test['name']}")
        print(f"使用者輸入: {test['user_input']}")
        print(f"原始回覆: {test['response']['text'][:50]}...")
        
        optimized = middleware.process_response(test['response'], test['user_input'])
        
        print(f"優化回覆: {optimized['text']}")
        
        if optimized['buttons']:
            print(f"優化按鈕: {[[btn['text'] for btn in group] for group in optimized['buttons']]}")
        
        original_len = len(test['response']['text'])
        optimized_len = len(optimized['text'])
        if original_len > 0:
            reduction = int((1 - optimized_len / original_len) * 100)
            print(f"文字減少: {reduction}%")
        
        print()

if __name__ == "__main__":
    test_global_middleware()