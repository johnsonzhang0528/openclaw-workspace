#!/usr/bin/env python3
"""
全域回覆內容優化器
優化所有類型的回覆，降低閱讀成本
"""

import re
from typing import Dict, List, Optional, Tuple

class GlobalResponseOptimizer:
    """全域回覆優化器 - 適用於所有類型的回覆"""
    
    def __init__(self):
        # 優化規則配置
        self.optimization_rules = {
            # 問候語優化
            "greeting": {
                "patterns": [
                    r"你好.*歡迎.*幫助",
                    r"嗨.*剛剛.*重新啟動",
                    r"Hello.*assistant.*help"
                ],
                "replacement": "👋 需要什麼協助？"
            },
            
            # 確認語優化
            "confirmation": {
                "patterns": [
                    r"好的.*明白.*理解",
                    r"了解.*清楚.*收到",
                    r"我理解.*你的需求"
                ],
                "replacement": "✅ 了解"
            },
            
            # 解釋性文字優化
            "explanation": {
                "patterns": [
                    r"這是一個.*功能.*能夠",
                    r"讓我.*解釋.*一下",
                    r"首先.*然後.*最後"
                ],
                "replacement": lambda text: self.optimize_explanation(text)
            },
            
            # 問題優化
            "question": {
                "patterns": [
                    r"你想.*做什麼",
                    r"需要.*幫助.*嗎",
                    r"有什麼.*問題"
                ],
                "replacement": "❓ 需要什麼？"
            },
            
            # 列表優化
            "list": {
                "patterns": [
                    r"1\..*\n2\..*\n3\..*",
                    r"首先.*\n其次.*\n最後.*"
                ],
                "replacement": self.optimize_list
            },
            
            # 技術說明優化
            "technical": {
                "patterns": [
                    r"系統.*架構.*設計",
                    r"技術.*實現.*細節",
                    r"代碼.*邏輯.*流程"
                ],
                "replacement": "⚙️ 技術細節："
            },
            
            # 錯誤訊息優化
            "error": {
                "patterns": [
                    r"錯誤.*發生.*問題",
                    r"無法.*執行.*失敗",
                    r"抱歉.*遇到.*困難"
                ],
                "replacement": "❌ 錯誤："
            },
            
            # 成功訊息優化
            "success": {
                "patterns": [
                    r"成功.*完成.*搞定",
                    r"已經.*設定.*好了",
                    r"完成.*設定.*配置"
                ],
                "replacement": "✅ 完成"
            },
            
            # 建議優化
            "suggestion": {
                "patterns": [
                    r"建議.*可以.*嘗試",
                    r"推薦.*使用.*方法",
                    r"最好.*應該.*考慮"
                ],
                "replacement": "💡 建議："
            }
        }
        
        # 通用優化規則
        self.general_rules = [
            # 移除冗餘問候語
            (r"^(很高興|非常榮幸|我很開心).*幫助", ""),
            
            # 簡化確認語
            (r"^(好的|明白了|了解).*(!|。)$", "✅"),
            
            # 縮短解釋性開頭
            (r"^(讓我|我要|我將).*(解釋|說明|介紹)", "📌"),
            
            # 優化問題結尾
            (r"(\?|嗎？)$", "？"),
            
            # 移除多餘的客套話
            (r"(請|麻煩|勞駕).*(你|您)", ""),
            
            # 簡化感謝語
            (r"謝謝.*(!|。|！)$", "🙏"),
            
            # 優化選項呈現
            (r"選項\s*(一|二|三|1|2|3)[：:]\s*", "• "),
            
            # 縮短網址說明
            (r"網址是.*(http[s]?://\S+)", "🔗"),
            
            # 簡化時間說明
            (r"(\d+)分鐘.*(前|後)", r"\1m"),
            (r"(\d+)小時.*(前|後)", r"\1h"),
            (r"(\d+)天.*(前|後)", r"\1d"),
            
            # 優化數字列表
            (r"(\d+)\.\s+", r"🔸 "),
            
            # 移除重複標點
            (r"!!+", "!"),
            (r"。。+", "。"),
            (r"？？+", "？"),
            
            # 簡化強調文字
            (r"\*\*(.*?)\*\*", r"【\1】"),
            (r"_(.*?)_", r"「\1」"),
            
            # 優化換行
            (r"\n{3,}", "\n\n"),
            
            # 移除尾部空格
            (r"\s+$", ""),
            
            # 優化中英文混排空格
            (r"([a-zA-Z])([\u4e00-\u9fff])", r"\1 \2"),
            (r"([\u4e00-\u9fff])([a-zA-Z])", r"\1 \2")
        ]
    
    def optimize_response(self, text: str, context: str = "") -> str:
        """
        優化回覆內容
        Args:
            text: 原始回覆文字
            context: 對話上下文（可選）
        Returns:
            優化後的回覆文字
        """
        if not text or not text.strip():
            return text
        
        original_text = text
        optimized_text = text
        
        # 第一步：應用特定規則優化
        optimized_text = self.apply_specific_rules(optimized_text, context)
        
        # 第二步：應用通用規則優化
        optimized_text = self.apply_general_rules(optimized_text)
        
        # 第三步：結構優化
        optimized_text = self.optimize_structure(optimized_text)
        
        # 第四步：長度控制
        optimized_text = self.control_length(optimized_text)
        
        # 第五步：視覺優化
        optimized_text = self.visual_optimization(optimized_text)
        
        # 記錄優化效果
        if len(original_text) > 0:
            reduction = int((1 - len(optimized_text) / len(original_text)) * 100)
            if reduction > 10:  # 只有顯著優化才記錄
                print(f"優化效果: {len(original_text)} → {len(optimized_text)} 字元 (減少 {reduction}%)")
        
        return optimized_text
    
    def apply_specific_rules(self, text: str, context: str) -> str:
        """應用特定規則優化"""
        # 根據上下文選擇優化策略
        context_lower = context.lower() if context else ""
        text_lower = text.lower()
        
        # 檢查是否需要特定優化
        for rule_name, rule in self.optimization_rules.items():
            for pattern in rule["patterns"]:
                if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                    if callable(rule["replacement"]):
                        return rule["replacement"](text)
                    else:
                        # 保留原意的關鍵內容
                        if rule_name == "error":
                            # 提取錯誤訊息
                            error_match = re.search(r"錯誤[：:]?\s*(.+)", text, re.IGNORECASE)
                            if error_match:
                                return f"❌ {error_match.group(1)[:50]}"
                        
                        return rule["replacement"]
        
        return text
    
    def apply_general_rules(self, text: str) -> str:
        """應用通用規則優化"""
        optimized = text
        
        for pattern, replacement in self.general_rules:
            optimized = re.sub(pattern, replacement, optimized, flags=re.IGNORECASE | re.MULTILINE)
        
        return optimized
    
    def optimize_list(self, text: str) -> str:
        """優化列表內容"""
        lines = text.split('\n')
        optimized_lines = []
        
        for line in lines:
            # 簡化列表項目
            line = re.sub(r"^(\d+)[\.、]?\s*", "• ", line)
            line = re.sub(r"^[（(][一二三四五六七八九十][）)]\s*", "• ", line)
            
            # 移除冗詞
            line = re.sub(r"(首先|其次|然後|接著|最後|另外|此外|同時)\s*", "", line)
            
            # 縮短過長項目
            if len(line) > 60:
                line = line[:57] + "..."
            
            optimized_lines.append(line)
        
        return '\n'.join(optimized_lines)
    
    def optimize_explanation(self, text: str) -> str:
        """優化解釋性文字"""
        # 提取關鍵句子
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return "📋"
        
        # 取最重要的句子（通常是最後一句或包含關鍵詞的句子）
        important_sentences = []
        
        # 優先取最後一句（通常是結論）
        if sentences:
            important_sentences.append(sentences[-1])
        
        # 如果有包含「功能」、「系統」、「能夠」等關鍵詞的句子
        keywords = ["功能", "系統", "能夠", "可以", "實現", "提供"]
        for sentence in sentences[:-1]:  # 排除已經取的最後一句
            if any(keyword in sentence for keyword in keywords):
                if sentence not in important_sentences:
                    important_sentences.append(sentence)
                    break
        
        # 如果還是沒有，取第一句
        if not important_sentences and sentences:
            important_sentences.append(sentences[0])
        
        # 組裝
        if len(important_sentences) == 1:
            result = important_sentences[0]
            if len(result) > 50:
                result = result[:47] + "..."
            return f"📋 {result}"
        else:
            result = ' '.join(important_sentences)
            if len(result) > 80:
                result = result[:77] + "..."
            return f"📋 {result}"
    
    def optimize_structure(self, text: str) -> str:
        """優化回覆結構"""
        lines = text.split('\n')
        
        if len(lines) <= 3:
            return text
        
        # 識別段落
        paragraphs = []
        current_para = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_para:
                    paragraphs.append(' '.join(current_para))
                    current_para = []
            else:
                current_para.append(line)
        
        if current_para:
            paragraphs.append(' '.join(current_para))
        
        # 優化段落結構
        optimized_paragraphs = []
        for para in paragraphs:
            if len(para) > 100:
                # 長段落分割
                sentences = re.split(r'[。！？!?]', para)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                if len(sentences) > 1:
                    # 取前兩個句子
                    optimized_para = '。'.join(sentences[:2]) + '。'
                    if len(sentences) > 2:
                        optimized_para += "（詳細內容可進一步詢問）"
                else:
                    optimized_para = para[:80] + "..."
            else:
                optimized_para = para
            
            optimized_paragraphs.append(optimized_para)
        
        # 重新組裝
        return '\n\n'.join(optimized_paragraphs)
    
    def control_length(self, text: str, max_length: int = 500) -> str:
        """控制回覆長度"""
        if len(text) <= max_length:
            return text
        
        # 如果太長，進行摘要
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 3:
            # 直接截斷
            return text[:max_length-3] + "..."
        
        # 取最重要的句子（假設開頭和結尾較重要）
        important_sentences = []
        if sentences:
            important_sentences.append(sentences[0])  # 第一句
        
        if len(sentences) > 1:
            important_sentences.append(sentences[-1])  # 最後一句
        
        # 如果有中間的重要句子（包含關鍵詞）
        keywords = ["重要", "關鍵", "必須", "需要", "建議", "注意"]
        for i in range(1, len(sentences)-1):
            if any(keyword in sentences[i] for keyword in keywords):
                important_sentences.append(sentences[i])
                if len(important_sentences) >= 3:
                    break
        
        optimized = '。'.join(important_sentences) + '。'
        
        if len(optimized) > max_length:
            optimized = optimized[:max_length-3] + "..."
        
        return optimized
    
    def visual_optimization(self, text: str) -> str:
        """視覺優化"""
        if not text:
            return text
        
        # 添加適當的視覺元素
        lines = text.split('\n')
        optimized_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                optimized_lines.append("")
                continue
            
            # 根據內容添加圖示
            if i == 0 and len(lines) > 1:  # 可能是標題
                if len(line) < 20 and not line.startswith(("•", "🔸", "✅", "❌", "❓", "💡", "📌")):
                    if "?" in line or "？" in line:
                        line = "❓ " + line
                    elif "錯誤" in line or "失敗" in line:
                        line = "❌ " + line
                    elif "成功" in line or "完成" in line:
                        line = "✅ " + line
                    elif "建議" in line or "推薦" in line:
                        line = "💡 " + line
                    else:
                        line = "📌 " + line
            
            optimized_lines.append(line)
        
        result = '\n'.join(optimized_lines)
        
        # 確保結尾簡潔
        result = re.sub(r'[。！？!?]\s*$', '', result)
        
        return result
    
    def optimize_conversation_flow(self, messages: List[Dict]) -> List[Dict]:
        """優化對話流程（批量處理）"""
        optimized_messages = []
        
        for msg in messages:
            if msg.get("role") == "assistant":
                optimized_content = self.optimize_response(msg.get("content", ""))
                optimized_msg = msg.copy()
                optimized_msg["content"] = optimized_content
                optimized_messages.append(optimized_msg)
            else:
                optimized_messages.append(msg)
        
        return optimized_messages

# 測試函數
def test_global_optimizer():
    """測試全域優化器"""
    print("=== 測試全域回覆內容優化器 ===\n")
    
    optimizer = GlobalResponseOptimizer()
    
    # 測試案例
    test_cases = [
        {
            "name": "問候語",
            "input": "你好！我是你的 AI 助手，剛剛重新啟動了。今天想讓我幫你做什麼呢？",
            "context": "greeting"
        },
        {
            "name": "技術解釋",
            "input": "這是一個智慧型的議題追蹤系統，能夠自動偵測新議題並建立 issue 列表。首先，系統會監聽對話內容，然後計算相似度，最後在主題轉換時建立新議題。",
            "context": "explanation"
        },
        {
            "name": "錯誤訊息",
            "input": "抱歉，執行時發生錯誤：無法載入模組 'nonexistent_module'，請檢查安裝。",
            "context": "error"
        },
        {
            "name": "成功確認",
            "input": "好的，已經成功完成設定！系統現在可以正常運作了。",
            "context": "success"
        },
        {
            "name": "建議列表",
            "input": "建議你可以：\n1. 先備份重要資料\n2. 檢查系統設定\n3. 測試功能是否正常\n4. 如有問題請回報",
            "context": "suggestion"
        },
        {
            "name": "複雜解釋",
            "input": "首先，讓我解釋一下這個功能的運作原理。系統會先收集使用者輸入，然後進行語義分析，接著比對現有議題，最後決定是否建立新議題。這個過程需要考慮多個因素，包括主題相似度、討論歷史和上下文關聯性。",
            "context": "technical"
        }
    ]
    
    for test in test_cases:
        print(f"測試: {test['name']}")
        print(f"輸入: {test['input']}")
        
        optimized = optimizer.optimize_response(test['input'], test['context'])
        
        print(f"優化: {optimized}")
        
        reduction = int((1 - len(optimized) / len(test['input'])) * 100)
        print(f"減少: {reduction}%")
        print()

if __name__ == "__main__":
    test_global_optimizer()