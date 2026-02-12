#!/usr/bin/env python3
"""
議題系統回報內容優化器
目標：將閱讀成本優化至最小
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

class IssueContentOptimizer:
    """議題內容優化器"""
    
    @staticmethod
    def optimize_issue_list(issues: List[Dict], title: str = "議題列表") -> str:
        """
        優化議題列表顯示
        目標：極簡、可掃描、高資訊密度
        """
        if not issues:
            return f"📋 {title} (0)\n\n📭 目前沒有議題"
        
        # 計算時間差（相對時間）
        now = datetime.now()
        
        lines = [f"📋 {title} ({len(issues)})", ""]
        
        for i, issue in enumerate(issues, 1):
            # 狀態符號
            status_emoji = "🟢" if issue["status"] == "open" else "🔴"
            
            # 簡化標題（取前幾個關鍵字）
            simple_title = IssueContentOptimizer.simplify_title(issue["title"])
            
            # 相對時間
            updated_time = datetime.fromisoformat(issue["updated_at"])
            time_diff = now - updated_time
            minutes_ago = int(time_diff.total_seconds() / 60)
            
            if minutes_ago < 1:
                time_str = "剛剛"
            elif minutes_ago < 60:
                time_str = f"{minutes_ago}m前"
            else:
                hours_ago = minutes_ago // 60
                time_str = f"{hours_ago}h前"
            
            # 組裝行
            line = f"{status_emoji} {i}. {simple_title} [{time_str}]"
            lines.append(line)
        
        lines.append("")
        lines.append("📌 點擊查看詳情")
        
        return "\n".join(lines)
    
    @staticmethod
    def optimize_issue_detail(issue: Dict) -> str:
        """
        優化議題詳情顯示
        目標：關鍵資訊前置，減少冗餘
        """
        # 狀態和標題
        status_emoji = "🟢" if issue["status"] == "open" else "🔴"
        simple_title = IssueContentOptimizer.simplify_title(issue["title"])
        
        # 時間資訊
        created_time = datetime.fromisoformat(issue["created_at"])
        updated_time = datetime.fromisoformat(issue["updated_at"])
        now = datetime.now()
        
        created_diff = now - created_time
        updated_diff = now - updated_time
        
        created_min = int(created_diff.total_seconds() / 60)
        updated_min = int(updated_diff.total_seconds() / 60)
        
        # 討論次數
        discussion_count = len(issue.get("discussions", []))
        
        lines = []
        
        # 第一行：狀態 + 標題
        lines.append(f"{status_emoji} {simple_title}")
        
        # 第二行：時間 + 討論次數
        time_info = []
        if updated_min < 60:
            time_info.append(f"⏰ {updated_min}m前")
        else:
            time_info.append(f"⏰ {updated_min//60}h前")
        
        time_info.append(f"💬 {discussion_count}次")
        lines.append(" • ".join(time_info))
        
        # 空行分隔
        lines.append("")
        
        # 最後討論（如果有）
        if issue.get("last_discussion"):
            last_discussion = issue["last_discussion"]
            if len(last_discussion) > 50:
                last_discussion = last_discussion[:47] + "..."
            lines.append(f"📌 {last_discussion}")
            lines.append("")
        
        # 操作提示
        lines.append("🛠️ 操作：")
        
        return "\n".join(lines)
    
    @staticmethod
    def optimize_issue_history(issues: List[Dict]) -> str:
        """
        優化歷史議題顯示
        """
        if not issues:
            return "📚 歷史議題 (0)\n\n📭 沒有歷史議題"
        
        now = datetime.now()
        
        lines = [f"📚 歷史議題 ({len(issues)})", ""]
        
        for i, issue in enumerate(issues, 1):
            # 簡化標題
            simple_title = IssueContentOptimizer.simplify_title(issue["title"])
            
            # 時間計算
            created_time = datetime.fromisoformat(issue["created_at"])
            updated_time = datetime.fromisoformat(issue["updated_at"])
            
            created_diff = now - created_time
            updated_diff = now - updated_time
            
            created_min = int(created_diff.total_seconds() / 60)
            updated_min = int(updated_diff.total_seconds() / 60)
            
            # 時間字串
            if created_min < 60:
                created_str = f"{created_min}m前"
            else:
                created_str = f"{created_min//60}h前"
            
            if updated_min < 60:
                updated_str = f"{updated_min}m前"
            else:
                updated_str = f"{updated_min//60}h前"
            
            # 組裝行
            line = f"🔴 {i}. {simple_title}"
            lines.append(line)
            lines.append(f"   ⏰ 建立: {created_str} • 關閉: {updated_str}")
            lines.append("")
        
        lines.append("📌 點擊查看摘要")
        
        return "\n".join(lines)
    
    @staticmethod
    def optimize_full_history(issue: Dict) -> str:
        """
        優化完整歷史記錄顯示
        """
        simple_title = IssueContentOptimizer.simplify_title(issue["title"])
        
        created_time = datetime.fromisoformat(issue["created_at"])
        updated_time = datetime.fromisoformat(issue["updated_at"])
        
        lines = []
        
        # 標題和狀態
        status_text = "已關閉" if issue["status"] == "closed" else "開啟"
        lines.append(f"📖 {simple_title} [{status_text}]")
        lines.append("")
        
        # 時間資訊（簡化）
        created_str = created_time.strftime("%m/%d %H:%M")
        updated_str = updated_time.strftime("%m/%d %H:%M")
        lines.append(f"🕒 {created_str} → {updated_str}")
        lines.append("")
        
        # 摘要（如果有）
        if issue.get("full_summary"):
            summary = issue["full_summary"]
            if len(summary) > 100:
                summary = summary[:97] + "..."
            lines.append(f"📋 {summary}")
            lines.append("")
        
        # 討論統計
        discussion_count = len(issue.get("discussions", []))
        lines.append(f"💬 共 {discussion_count} 次討論")
        
        return "\n".join(lines)
    
    @staticmethod
    def simplify_title(title: str, max_words: int = 4) -> str:
        """
        簡化議題標題
        移除冗詞，保留關鍵字
        """
        # 移除常見冗詞（更完整的列表）
        stop_words = {
            "然後", "關於", "我們", "需要", "討論", "分析", "覺得", "還要", "還要看",
            "來", "的", "了", "在", "是", "有", "和", "就", "都", "而", "及", "與", "或",
            "首先", "接著", "最後", "另外", "其他", "一些", "幾個", "各種", "這個", "那個",
            "進行", "實施", "執行", "完成", "開始", "結束", "繼續"
        }
        
        # 分割詞彙（中文和英文）
        words = re.findall(r'[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}', title)
        
        # 過濾停用詞
        filtered_words = [w for w in words if w not in stop_words]
        
        # 如果過濾後太短，保留原詞但限制長度
        if not filtered_words:
            # 取前幾個詞，但跳過停用詞
            all_words = re.findall(r'[\u4e00-\u9fff]+|[A-Za-z]+', title)
            filtered_words = [w for w in all_words if w not in stop_words][:max_words]
        
        # 限制字數
        if len(filtered_words) > max_words:
            filtered_words = filtered_words[:max_words]
        
        # 重新組裝（用空格分隔）
        simplified = " ".join(filtered_words) if filtered_words else title[:15]
        
        # 確保長度合理
        if len(simplified) > 20:
            simplified = simplified[:17] + "..."
        
        return simplified
    
    @staticmethod
    def optimize_button_text(text: str) -> str:
        """
        優化按鈕文字
        """
        # 移除冗詞，保留核心意思
        optimizations = {
            "重新整理": "🔄",
            "查看歷史議題": "📚 歷史",
            "返回列表": "🔙 列表",
            "關閉議題": "✅ 關閉",
            "繼續討論": "📝 繼續",
            "重新開啟": "🔄 開啟",
            "查看完整記錄": "📖 記錄",
            "返回歷史列表": "🔙 歷史",
            "查看議題": "📝 查看",
            "建立新議題": "🆕 新建"
        }
        
        return optimizations.get(text, text)
    
    @staticmethod
    def optimize_system_message(message: str) -> str:
        """
        優化系統訊息
        """
        # 移除冗餘的問候語和描述
        optimizations = {
            "我偵測到你在討論議題相關的事情。需要我幫你：\n1. 查看當前議題列表\n2. 關閉當前議題\n3. 建立新議題嗎？": 
                "🔍 偵測到議題討論\n\n需要：\n1. 📋 議題列表\n2. ✅ 關閉議題\n3. 🆕 新建議題",
            
            "🔍 *偵測到新議題*\n\n已建立新議題: {title}\n議題ID: {id}": 
                "🆕 新議題: {title}",
            
            "✅ *議題已關閉*\n\n📝 {title}\n\n📋 最終摘要已生成，可透過 /issueHistory 查看完整記錄。":
                "✅ 已關閉: {title}\n\n📋 摘要已保存",
            
            "🔄 *議題已重新開啟*\n\n議題已恢復為開啟狀態，可以繼續討論。":
                "🔄 已重新開啟\n\n可繼續討論"
        }
        
        # 尋找匹配的優化
        for old, new in optimizations.items():
            if old in message:
                return new
        
        # 通用優化：移除多餘的星號和換行
        message = re.sub(r'\*\*(.*?)\*\*', r'\1', message)  # 移除粗體標記
        message = re.sub(r'\n{3,}', '\n\n', message)  # 減少多餘空行
        
        return message

# 測試函數
def test_optimizer():
    """測試優化器"""
    print("=== 測試議題內容優化器 ===\n")
    
    optimizer = IssueContentOptimizer()
    
    # 測試資料
    test_issues = [
        {
            "id": "abc123",
            "title": "回到 GSC 分析 我覺得還需要看排名變化",
            "status": "open",
            "created_at": "2026-02-11T03:18:00",
            "updated_at": "2026-02-11T03:21:00",
            "last_discussion": "需要看排名變化來評估SEO效果",
            "discussions": [{"summary": "測試討論"}]
        },
        {
            "id": "def456",
            "title": "然後分析關鍵字表現和點擊率",
            "status": "open",
            "created_at": "2026-02-11T03:15:00",
            "updated_at": "2026-02-11T03:25:00",
            "last_discussion": "關鍵字表現需要對比歷史數據",
            "discussions": [{"summary": "測試討論"}, {"summary": "另一個討論"}]
        }
    ]
    
    test_issue_detail = {
        "id": "abc123",
        "title": "回到 GSC 分析 我覺得還需要看排名變化",
        "status": "open",
        "created_at": "2026-02-11T03:18:00",
        "updated_at": "2026-02-11T03:21:00",
        "last_discussion": "需要看排名變化來評估SEO效果，這對於了解網站表現很重要",
        "discussions": [{"summary": "測試討論"}],
        "full_summary": "討論了GSC數據分析，重點關注排名變化對SEO效果的影響。"
    }
    
    print("1. 議題列表優化:")
    print(optimizer.optimize_issue_list(test_issues))
    print()
    
    print("2. 議題詳情優化:")
    print(optimizer.optimize_issue_detail(test_issue_detail))
    print()
    
    print("3. 標題簡化測試:")
    test_titles = [
        "然後分析關鍵字表現和點擊率",
        "關於多任務議題同步討論可行性",
        "我們需要考慮上下文切換的效能問題",
        "GSC數據分析技能提升方案"
    ]
    
    for title in test_titles:
        simplified = optimizer.simplify_title(title)
        print(f"   '{title}' → '{simplified}'")
    
    print()
    print("4. 系統訊息優化:")
    test_messages = [
        "我偵測到你在討論議題相關的事情。需要我幫你：\n1. 查看當前議題列表\n2. 關閉當前議題\n3. 建立新議題嗎？",
        "🔍 *偵測到新議題*\n\n已建立新議題: 測試議題\n議題ID: abc123",
        "✅ *議題已關閉*\n\n📝 測試議題\n\n📋 最終摘要已生成，可透過 /issueHistory 查看完整記錄。"
    ]
    
    for msg in test_messages:
        optimized = optimizer.optimize_system_message(msg)
        print(f"   原始: {msg[:50]}...")
        print(f"   優化: {optimized[:50]}...")
        print()

if __name__ == "__main__":
    test_optimizer()