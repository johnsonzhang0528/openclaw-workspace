#!/usr/bin/env python3
"""
智能回覆優化器
根據內容類型進行不同程度的優化
"""

import re
from typing import Dict, List, Optional, Tuple

class SmartResponseOptimizer:
    """智能回覆優化器"""
    
    def __init__(self):
        # 內容類型檢測規則
        self.content_type_rules = {
            "greeting": {
                "patterns": [r"你好", r"嗨", r"hello", r"hi", r"歡迎"],
                "optimization_level": "high"  # 高度優化
            },
            "explanation": {
                "patterns": [r"解釋", r"說明", r"介紹", r"功能", r"原理"],
                "optimization_level": "medium"  # 中度優化
            },
            "instruction": {
                "patterns": [r"如何", r"怎麼", r"步驟", r"方法", r"操作"],
                "optimization_level": "low"  # 低度優化（保留細節）
            },
            "error": {
                "patterns": [r"錯誤", r"失敗", r"無法", r"問題", r"異常"],
                "optimization_level": "medium"
            },
            "success": {
                "patterns": [r"成功", r"完成", r"好了", r"搞定", r"正常"],
                "optimization_level": "high"
            },
            "question": {
                "patterns": [r"嗎？", r"嗎\?", r"什麼", r"如何", r"為什麼"],
                "optimization_level": "low"
            },
            "list": {
                "patterns": [r"\d+\.", r"•", r"首先.*其次", r"一、.*二、"],
                "optimization_level": "medium"
            },
            "technical": {
                "patterns": [r"系統", r"技術", r"代碼", r"API", r"設定"],
                "optimization_level": "medium"
            }
        }
        
        # 優化策略
        self.optimization_strategies = {
            "high": self.optimize_high,
            "medium": self.optimize_medium,
            "low": self.optimize_low
        }
    
    def detect_content_type(self, text: str) -> Tuple[str, str]:
        """
        檢測內容類型
        Returns: (類型, 優化等級)
        """
        text_lower = text.lower()
        
        for content_type, rules in self.content_type_rules.items():
            for pattern in rules["patterns"]:
                if re.search(pattern, text_lower):
                    return content_type, rules["optimization_level"]
        
        # 默認類型
        return "general", "medium"
    
    def optimize_response(self, text: str, context: str = "") -> str:
        """
        智能優化回覆
        """
        if not text or len(text.strip()) < 5:
            return text
        
        # 檢測內容類型
        content_type, optimization_level = self.detect_content_type(text)
        
        # 應用對應的優化策略
        optimizer = self.optimization_strategies.get(optimization_level, self.optimize_medium)
        optimized_text = optimizer(text, content_type, context)
        
        # 確保優化後仍有內容
        if not optimized_text or len(optimized_text.strip()) < 2:
            # 回退到輕度優化
            optimized_text = self.optimize_low(text, content_type, context)
        
        return optimized_text
    
    def optimize_high(self, text: str, content_type: str, context: str) -> str:
        """高度優化 - 最大程度精簡"""
        # 基本清理
        text = self.basic_cleanup(text)
        
        if content_type == "greeting":
            return self.optimize_greeting(text)
        elif content_type == "success":
            return self.optimize_success(text)
        elif content_type == "error":
            return self.optimize_error(text)
        
        # 通用高度優化
        return self.aggressive_optimization(text)
    
    def optimize_medium(self, text: str, content_type: str, context: str) -> str:
        """中度優化 - 平衡精簡與資訊保留"""
        text = self.basic_cleanup(text)
        
        if content_type == "explanation":
            return self.optimize_explanation(text)
        elif content_type == "list":
            return self.optimize_list(text)
        elif content_type == "technical":
            return self.optimize_technical(text)
        
        # 通用中度優化
        return self.balanced_optimization(text)
    
    def optimize_low(self, text: str, content_type: str, context: str) -> str:
        """低度優化 - 主要清理格式，保留內容"""
        text = self.basic_cleanup(text)
        
        if content_type == "instruction":
            return self.optimize_instruction(text)
        elif content_type == "question":
            return self.optimize_question(text)
        
        # 通用低度優化
        return self.light_optimization(text)
    
    def basic_cleanup(self, text: str) -> str:
        """基本清理"""
        # 移除多餘空格
        text = re.sub(r'\s+', ' ', text)
        
        # 移除多餘標點
        text = re.sub(r'[。！？!?]{2,}', lambda m: m.group(0)[0], text)
        
        # 清理開頭結尾
        text = text.strip()
        
        return text
    
    def optimize_greeting(self, text: str) -> str:
        """優化問候語"""
        # 提取核心問候
        patterns = [
            r"(你好[！!]?).*",
            r"(嗨[！!]?).*",
            r"Hello.*",
            r"Hi.*"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                core = match.group(1)
                return f"{core} 需要什麼協助？"
        
        return "👋 需要協助？"
    
    def optimize_success(self, text: str) -> str:
        """優化成功訊息"""
        # 提取成功關鍵詞
        if "成功" in text or "完成" in text:
            # 提取具體完成事項
            match = re.search(r"(成功|完成).*?(設定|配置|安裝|建立)", text)
            if match:
                action = match.group(2)
                return f"✅ {action}完成"
        
        return "✅ 完成"
    
    def optimize_error(self, text: str) -> str:
        """優化錯誤訊息"""
        # 提取錯誤原因
        error_match = re.search(r"錯誤[：:]?\s*(.+)", text)
        if error_match:
            error_msg = error_match.group(1)
            if len(error_msg) > 50:
                error_msg = error_msg[:47] + "..."
            return f"❌ {error_msg}"
        
        return "❌ 發生錯誤"
    
    def optimize_explanation(self, text: str) -> str:
        """優化解釋性文字"""
        # 提取關鍵句子
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return "📋"
        
        # 尋找包含核心概念的句子
        core_keywords = ["功能", "系統", "能夠", "可以", "實現"]
        for sentence in sentences:
            if any(keyword in sentence for keyword in core_keywords):
                if len(sentence) > 60:
                    sentence = sentence[:57] + "..."
                return f"📋 {sentence}"
        
        # 取第一句
        first_sentence = sentences[0]
        if len(first_sentence) > 60:
            first_sentence = first_sentence[:57] + "..."
        return f"📋 {first_sentence}"
    
    def optimize_list(self, text: str) -> str:
        """優化列表內容"""
        lines = text.split('\n')
        optimized_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 簡化列表標記
            line = re.sub(r'^(\d+)[\.、]\s*', '• ', line)
            line = re.sub(r'^[（(][一二三四][）)]\s*', '• ', line)
            
            # 移除冗詞
            line = re.sub(r'^(首先|其次|然後|接著|最後|另外)\s*', '', line)
            
            # 控制長度
            if len(line) > 50:
                line = line[:47] + "..."
            
            optimized_lines.append(line)
        
        if not optimized_lines:
            return text
        
        return '\n'.join(optimized_lines)
    
    def optimize_technical(self, text: str) -> str:
        """優化技術內容"""
        # 提取技術要點
        tech_keywords = ["API", "設定", "配置", "參數", "系統", "模組"]
        
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        tech_sentences = []
        for sentence in sentences:
            if any(keyword in sentence for keyword in tech_keywords):
                tech_sentences.append(sentence)
                if len(tech_sentences) >= 2:
                    break
        
        if tech_sentences:
            result = ' '.join(tech_sentences)
            if len(result) > 80:
                result = result[:77] + "..."
            return f"⚙️ {result}"
        
        # 沒有技術關鍵詞，取第一句
        if sentences:
            first = sentences[0]
            if len(first) > 60:
                first = first[:57] + "..."
            return f"📝 {first}"
        
        return text
    
    def optimize_instruction(self, text: str) -> str:
        """優化操作說明"""
        # 保留步驟細節，但清理格式
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # 簡化但不刪除內容
                line = re.sub(r'^請\s*', '', line)
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def optimize_question(self, text: str) -> str:
        """優化問題"""
        # 簡化問題表述
        text = re.sub(r'^(我想|我要|請問|麻煩).*?(嗎？|嗎\?|什麼|如何)', '❓ ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def aggressive_optimization(self, text: str) -> str:
        """激進優化"""
        # 取第一句或關鍵部分
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return ""
        
        # 取最短的句子（通常最核心）
        shortest = min(sentences, key=len)
        if len(shortest) > 40:
            shortest = shortest[:37] + "..."
        
        return shortest
    
    def balanced_optimization(self, text: str) -> str:
        """平衡優化"""
        # 控制段落長度
        paragraphs = text.split('\n\n')
        optimized_paragraphs = []
        
        for para in paragraphs:
            if len(para) > 100:
                # 取前後部分
                sentences = re.split(r'[。！？!?]', para)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                if len(sentences) >= 2:
                    optimized = sentences[0] + '。' + sentences[-1] + '。'
                else:
                    optimized = para[:80] + "..."
            else:
                optimized = para
            
            optimized_paragraphs.append(optimized)
        
        return '\n\n'.join(optimized_paragraphs)
    
    def light_optimization(self, text: str) -> str:
        """輕度優化"""
        # 主要清理格式，保留內容
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s{2,}', ' ', text)
        text = text.strip()
        
        return text

# 測試函數
def test_smart_optimizer():
    """測試智能優化器"""
    print("=== 測試智能回覆優化器 ===\n")
    
    optimizer = SmartResponseOptimizer()
    
    test_cases = [
        {
            "input": "你好！我是你的 AI 助手，剛剛重新啟動了。今天想讓我幫你做什麼呢？",
            "expected_type": "greeting"
        },
        {
            "input": "這是一個智慧型的議題追蹤系統，能夠自動偵測新議題並建立 issue 列表。系統會監聽對話內容，計算相似度，在主題轉換時建立新議題。",
            "expected_type": "explanation"
        },
        {
            "input": "首先，請點擊設定按鈕。然後，選擇系統設定選項。最後，調整相關參數並儲存。",
            "expected_type": "instruction"
        },
        {
            "input": "抱歉，執行時發生錯誤：無法載入模組 'nonexistent_module'，請檢查安裝。",
            "expected_type": "error"
        },
        {
            "input": "好的，已經成功完成設定！系統現在可以正常運作了。",
            "expected_type": "success"
        },
        {
            "input": "你想知道如何設定系統嗎？還是有其他問題？",
            "expected_type": "question"
        },
        {
            "input": "1. 備份資料\n2. 檢查設定\n3. 測試功能\n4. 回報問題",
            "expected_type": "list"
        },
        {
            "input": "系統使用 Python 3.12，API 設定在 config.json 中，需要設定正確的參數。",
            "expected_type": "technical"
        }
    ]
    
    for test in test_cases:
        print(f"測試輸入: {test['input'][:50]}...")
        
        content_type, level = optimizer.detect_content_type(test['input'])
        print(f"檢測類型: {content_type} (預期: {test['expected_type']})")
        print(f"優化等級: {level}")
        
        optimized = optimizer.optimize_response(test['input'])
        print(f"優化結果: {optimized}")
        
        reduction = int((1 - len(optimized) / len(test['input'])) * 100)
        print(f"減少: {reduction}%")
        print()

if __name__ == "__main__":
    test_smart_optimizer()