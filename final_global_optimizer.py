#!/usr/bin/env python3
"""
最終全域優化器
整合到 OpenClaw 系統中，優化所有回覆內容
"""

import json
import sys
import os
from typing import Dict, List, Optional, Any

# 添加工作空間路徑
sys.path.append('/root/.openclaw/workspace')

try:
    from smart_response_optimizer import SmartResponseOptimizer
    HAS_SMART_OPTIMIZER = True
except ImportError as e:
    print(f"無法載入智能優化器: {e}")
    HAS_SMART_OPTIMIZER = False

class FinalGlobalOptimizer:
    """最終全域優化器"""
    
    def __init__(self):
        self.optimizer = SmartResponseOptimizer() if HAS_SMART_OPTIMIZER else None
        self.optimization_enabled = True
        
        # 優化統計
        self.stats = {
            "total_optimized": 0,
            "total_reduction": 0,
            "by_type": {}
        }
    
    def optimize_all_responses(self, response_data: Any, user_input: str = "") -> Any:
        """
        優化所有回覆內容
        支援多種輸入格式：
        1. 字串
        2. 字典（包含 text 和 buttons）
        3. 列表
        """
        if not self.optimization_enabled or not self.optimizer:
            return response_data
        
        if isinstance(response_data, str):
            return self.optimize_text(response_data, user_input)
        
        elif isinstance(response_data, dict):
            return self.optimize_dict(response_data, user_input)
        
        elif isinstance(response_data, list):
            return self.optimize_list(response_data, user_input)
        
        else:
            return response_data
    
    def optimize_text(self, text: str, context: str = "") -> str:
        """優化文字內容"""
        if not text or len(text.strip()) < 3:
            return text
        
        original_length = len(text)
        optimized = self.optimizer.optimize_response(text, context)
        
        # 記錄統計
        self.record_statistics(text, optimized)
        
        return optimized
    
    def optimize_dict(self, response_dict: Dict, user_input: str = "") -> Dict:
        """優化字典格式的回覆"""
        optimized_dict = response_dict.copy()
        
        # 優化文字內容
        if "text" in optimized_dict and optimized_dict["text"]:
            optimized_dict["text"] = self.optimize_text(optimized_dict["text"], user_input)
        
        # 優化按鈕文字
        if "buttons" in optimized_dict and optimized_dict["buttons"]:
            optimized_dict["buttons"] = self.optimize_buttons(optimized_dict["buttons"])
        
        # 添加優化標記
        if "metadata" not in optimized_dict:
            optimized_dict["metadata"] = {}
        optimized_dict["metadata"]["optimized"] = True
        
        return optimized_dict
    
    def optimize_list(self, response_list: List, user_input: str = "") -> List:
        """優化列表格式的回覆"""
        optimized_list = []
        
        for item in response_list:
            if isinstance(item, (str, dict, list)):
                optimized_item = self.optimize_all_responses(item, user_input)
                optimized_list.append(optimized_item)
            else:
                optimized_list.append(item)
        
        return optimized_list
    
    def optimize_buttons(self, buttons: List[List[Dict]]) -> List[List[Dict]]:
        """優化按鈕文字"""
        if not buttons:
            return buttons
        
        optimized_buttons = []
        
        for button_group in buttons:
            optimized_group = []
            for button in button_group:
                if isinstance(button, dict) and "text" in button:
                    optimized_button = button.copy()
                    original_text = button["text"]
                    
                    # 簡化按鈕文字
                    simplified = self.simplify_button_text(original_text)
                    optimized_button["text"] = simplified
                    
                    optimized_group.append(optimized_button)
                else:
                    optimized_group.append(button)
            
            optimized_buttons.append(optimized_group)
        
        return optimized_buttons
    
    def simplify_button_text(self, text: str) -> str:
        """簡化按鈕文字"""
        # 常見按鈕文字優化
        button_optimizations = {
            # 完全匹配
            "重新整理": "🔄",
            "查看詳情": "👀",
            "開始討論": "▶️",
            "關閉議題": "✅",
            "繼續討論": "↻",
            "返回列表": "🔙",
            "建立新議題": "🆕",
            "查看歷史": "📚",
            "確認": "✓",
            "取消": "✗",
            "是": "✅",
            "否": "❌",
            "好的": "👌",
            "明白了": "💡",
            "確定": "✓",
            "關閉": "❌",
            
            # 部分匹配
            "重新": "🔄",
            "查看": "👀",
            "開始": "▶️",
            "繼續": "↻",
            "返回": "🔙",
            "建立": "🆕",
            "歷史": "📚"
        }
        
        # 檢查完全匹配
        if text in button_optimizations:
            return button_optimizations[text]
        
        # 檢查部分匹配（按鈕文字包含關鍵詞）
        for key, value in button_optimizations.items():
            if key in text and len(key) > 1:  # 避免單字匹配
                # 替換關鍵詞
                return text.replace(key, value)
        
        # 如果文字太長，截斷並添加省略號
        if len(text) > 12:
            return text[:10] + ".."
        
        return text
    
    def record_statistics(self, original: str, optimized: str):
        """記錄優化統計"""
        if not original or not optimized:
            return
        
        self.stats["total_optimized"] += 1
        
        original_len = len(original)
        optimized_len = len(optimized)
        
        if original_len > 0:
            reduction = 1 - (optimized_len / original_len)
            self.stats["total_reduction"] += reduction
            
            # 檢測內容類型
            content_type = self.detect_content_type_simple(original)
            if content_type not in self.stats["by_type"]:
                self.stats["by_type"][content_type] = {
                    "count": 0,
                    "total_reduction": 0
                }
            
            self.stats["by_type"][content_type]["count"] += 1
            self.stats["by_type"][content_type]["total_reduction"] += reduction
    
    def detect_content_type_simple(self, text: str) -> str:
        """簡單檢測內容類型"""
        text_lower = text.lower()
        
        type_keywords = {
            "greeting": ["你好", "嗨", "hello", "hi", "歡迎"],
            "explanation": ["這是", "功能", "系統", "能夠", "可以"],
            "error": ["錯誤", "失敗", "無法", "問題", "異常"],
            "success": ["成功", "完成", "好了", "搞定"],
            "question": ["嗎？", "嗎\?", "什麼", "如何", "為什麼"],
            "list": ["1.", "2.", "3.", "•", "首先", "其次"],
            "technical": ["API", "設定", "配置", "參數", "代碼"]
        }
        
        for content_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return content_type
        
        return "general"
    
    def get_statistics(self) -> Dict:
        """取得優化統計"""
        stats = self.stats.copy()
        
        # 計算平均減少率
        if stats["total_optimized"] > 0:
            avg_reduction = stats["total_reduction"] / stats["total_optimized"]
            stats["average_reduction"] = f"{avg_reduction*100:.1f}%"
        
        # 計算各類型平均減少率
        for content_type, type_stats in stats["by_type"].items():
            if type_stats["count"] > 0:
                avg = type_stats["total_reduction"] / type_stats["count"]
                type_stats["average_reduction"] = f"{avg*100:.1f}%"
        
        return stats
    
    def enable_optimization(self, enabled: bool = True):
        """啟用/停用優化"""
        self.optimization_enabled = enabled
    
    def reset_statistics(self):
        """重設統計資料"""
        self.stats = {
            "total_optimized": 0,
            "total_reduction": 0,
            "by_type": {}
        }

# 全域實例
final_optimizer = None

def get_final_optimizer():
    """取得最終優化器實例"""
    global final_optimizer
    if final_optimizer is None:
        final_optimizer = FinalGlobalOptimizer()
    return final_optimizer

def optimize_for_openclaw(response_data: Any, user_input: str = "") -> Any:
    """
    OpenClaw 整合函數：優化所有回覆
    """
    optimizer = get_final_optimizer()
    return optimizer.optimize_all_responses(response_data, user_input)

# 測試函數
def test_final_optimizer():
    """測試最終優化器"""
    print("=== 測試最終全域優化器 ===\n")
    
    optimizer = get_final_optimizer()
    
    # 測試各種格式
    test_cases = [
        {
            "name": "純文字回覆",
            "input": "你好！我是你的 AI 助手，剛剛重新啟動了。今天想讓我幫你做什麼呢？",
            "type": "text"
        },
        {
            "name": "字典回覆（含按鈕）",
            "input": {
                "text": "這是一個智慧型的議題追蹤系統，能夠自動偵測新議題並建立 issue 列表。",
                "buttons": [
                    [{"text": "查看議題列表", "callback_data": "/issue"}],
                    [{"text": "查看歷史議題", "callback_data": "/issueHistory"}]
                ]
            },
            "type": "dict"
        },
        {
            "name": "錯誤回覆",
            "input": "抱歉，執行時發生錯誤：無法載入所需模組，請檢查系統設定。",
            "type": "text"
        },
        {
            "name": "成功回覆",
            "input": "好的，已經成功完成設定！系統現在可以正常運作了。",
            "type": "text"
        },
        {
            "name": "操作說明",
            "input": "首先，請點擊設定按鈕。然後，選擇系統設定選項。最後，調整相關參數並儲存。",
            "type": "text"
        }
    ]
    
    for test in test_cases:
        print(f"測試: {test['name']}")
        print(f"輸入類型: {test['type']}")
        
        if test['type'] == 'text':
            print(f"原始: {test['input'][:60]}...")
            optimized = optimizer.optimize_all_responses(test['input'])
            print(f"優化: {optimized}")
        elif test['type'] == 'dict':
            print(f"原始文字: {test['input']['text'][:60]}...")
            print(f"原始按鈕: {[[btn['text'] for btn in group] for group in test['input']['buttons']]}")
            
            optimized = optimizer.optimize_all_responses(test['input'])
            print(f"優化文字: {optimized['text']}")
            print(f"優化按鈕: {[[btn['text'] for btn in group] for group in optimized['buttons']]}")
        
        print()
    
    # 顯示統計
    print("優化統計:")
    stats = optimizer.get_statistics()
    print(json.dumps(stats, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_final_optimizer()