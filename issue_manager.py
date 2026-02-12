#!/usr/bin/env python3
"""
智慧議題追蹤系統 - 議題管理模組
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

class IssueManager:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.issues_dir = os.path.join(workspace_path, "issues")
        self.index_path = os.path.join(workspace_path, "issues_index.json")
        self.state_path = os.path.join(workspace_path, "system_state.json")
        
        # 確保目錄存在
        os.makedirs(self.issues_dir, exist_ok=True)
        
        # 載入索引和狀態
        self.load_index()
        self.load_state()
    
    def load_index(self):
        """載入議題索引"""
        if os.path.exists(self.index_path):
            with open(self.index_path, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {
                "issues": [],
                "last_issue_id": 0,
                "settings": {
                    "similarity_threshold": 0.3,
                    "current_issue_id": None,
                    "auto_detection": True
                }
            }
    
    def save_index(self):
        """儲存議題索引"""
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def load_state(self):
        """載入系統狀態"""
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "current_issue_id": None,
                "last_message": "",
                "last_topic": "",
                "conversation_history": []
            }
    
    def save_state(self):
        """儲存系統狀態"""
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def create_issue(self, title: str, initial_message: str = "") -> str:
        """建立新議題"""
        issue_id = str(uuid.uuid4())[:8]
        
        issue = {
            "id": issue_id,
            "title": title,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_discussion": initial_message[:200] if initial_message else "新議題建立",
            "discussions": [],
            "full_summary": ""
        }
        
        # 儲存議題檔案
        issue_path = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_path, 'w', encoding='utf-8') as f:
            json.dump(issue, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        self.index["issues"].append({
            "id": issue_id,
            "title": title,
            "status": "open",
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"]
        })
        self.index["last_issue_id"] += 1
        self.save_index()
        
        return issue_id
    
    def get_issue(self, issue_id: str) -> Optional[Dict]:
        """取得議題詳細資訊"""
        issue_path = os.path.join(self.issues_dir, f"{issue_id}.json")
        if not os.path.exists(issue_path):
            return None
        
        with open(issue_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def update_issue(self, issue_id: str, message: str, summary: str = "") -> bool:
        """更新議題討論內容"""
        issue = self.get_issue(issue_id)
        if not issue:
            return False
        
        # 新增討論記錄
        discussion = {
            "timestamp": datetime.now().isoformat(),
            "content": message,
            "summary": summary if summary else self.generate_summary(message)
        }
        
        issue["discussions"].append(discussion)
        issue["updated_at"] = datetime.now().isoformat()
        issue["last_discussion"] = discussion["summary"]
        
        # 儲存議題
        issue_path = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_path, 'w', encoding='utf-8') as f:
            json.dump(issue, f, ensure_ascii=False, indent=2)
        
        # 更新索引中的更新時間
        for idx, issue_info in enumerate(self.index["issues"]):
            if issue_info["id"] == issue_id:
                self.index["issues"][idx]["updated_at"] = issue["updated_at"]
                break
        
        self.save_index()
        return True
    
    def close_issue(self, issue_id: str, final_summary: str = "") -> bool:
        """關閉議題"""
        issue = self.get_issue(issue_id)
        if not issue:
            return False
        
        issue["status"] = "closed"
        issue["updated_at"] = datetime.now().isoformat()
        issue["full_summary"] = final_summary if final_summary else self.generate_full_summary(issue)
        
        # 儲存議題
        issue_path = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_path, 'w', encoding='utf-8') as f:
            json.dump(issue, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        for idx, issue_info in enumerate(self.index["issues"]):
            if issue_info["id"] == issue_id:
                self.index["issues"][idx]["status"] = "closed"
                self.index["issues"][idx]["updated_at"] = issue["updated_at"]
                break
        
        self.save_index()
        return True
    
    def reopen_issue(self, issue_id: str) -> bool:
        """重新開啟議題"""
        issue = self.get_issue(issue_id)
        if not issue:
            return False
        
        issue["status"] = "open"
        issue["updated_at"] = datetime.now().isoformat()
        
        # 儲存議題
        issue_path = os.path.join(self.issues_dir, f"{issue_id}.json")
        with open(issue_path, 'w', encoding='utf-8') as f:
            json.dump(issue, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        for idx, issue_info in enumerate(self.index["issues"]):
            if issue_info["id"] == issue_id:
                self.index["issues"][idx]["status"] = "open"
                self.index["issues"][idx]["updated_at"] = issue["updated_at"]
                break
        
        self.save_index()
        return True
    
    def get_open_issues(self) -> List[Dict]:
        """取得所有開啟的議題"""
        open_issues = []
        for issue_info in self.index["issues"]:
            if issue_info["status"] == "open":
                open_issues.append(issue_info)
        
        # 按更新時間排序（最新的在前）
        open_issues.sort(key=lambda x: x["updated_at"], reverse=True)
        return open_issues
    
    def get_closed_issues(self) -> List[Dict]:
        """取得所有已關閉的議題"""
        closed_issues = []
        for issue_info in self.index["issues"]:
            if issue_info["status"] == "closed":
                closed_issues.append(issue_info)
        
        # 按更新時間排序（最新的在前）
        closed_issues.sort(key=lambda x: x["updated_at"], reverse=True)
        return closed_issues
    
    def detect_topic_change(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        偵測主題是否轉換
        返回: (是否轉換, 建議的議題標題)
        """
        if not self.state["last_message"]:
            self.state["last_message"] = message
            self.state["last_topic"] = self.extract_topic(message)
            self.save_state()
            return False, None
        
        # 簡單的主題相似度計算（基於關鍵字）
        current_topic = self.extract_topic(message)
        last_topic = self.state["last_topic"]
        
        similarity = self.calculate_similarity(current_topic, last_topic)
        
        # 更新狀態
        self.state["last_message"] = message
        self.state["last_topic"] = current_topic
        self.save_state()
        
        # 如果相似度低於閾值，認為主題轉換
        if similarity < self.index["settings"]["similarity_threshold"]:
            return True, current_topic
        
        return False, None
    
    def extract_topic(self, text: str) -> str:
        """從文字中提取主題關鍵字"""
        # 移除標點和常見詞
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "都", "而", "及", "與", "或"}
        words = re.findall(r'[\u4e00-\u9fff]+|[A-Za-z]+', text)
        
        # 過濾停用詞，取前5個關鍵字
        keywords = [word for word in words if word not in stop_words][:5]
        return " ".join(keywords)
    
    def calculate_similarity(self, topic1: str, topic2: str) -> float:
        """計算兩個主題的相似度（簡單的Jaccard相似度）"""
        if not topic1 or not topic2:
            return 0.0
        
        set1 = set(topic1.split())
        set2 = set(topic2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def generate_summary(self, text: str, max_length: int = 100) -> str:
        """生成討論摘要"""
        # 簡單的摘要生成：取前幾個句子
        sentences = re.split(r'[。！？!?]', text)
        summary = sentences[0] if sentences else text[:max_length]
        
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def generate_full_summary(self, issue: Dict) -> str:
        """生成議題完整摘要"""
        discussions = issue.get("discussions", [])
        if not discussions:
            return issue.get("title", "") + " - 無詳細討論記錄"
        
        # 合併所有討論摘要
        summaries = [d.get("summary", "") for d in discussions if d.get("summary")]
        full_summary = " | ".join(summaries)
        
        if len(full_summary) > 500:
            full_summary = full_summary[:497] + "..."
        
        return full_summary
    
    def set_current_issue(self, issue_id: Optional[str]):
        """設定當前討論的議題"""
        self.state["current_issue_id"] = issue_id
        self.save_state()
    
    def get_current_issue(self) -> Optional[Dict]:
        """取得當前議題"""
        if not self.state["current_issue_id"]:
            return None
        
        return self.get_issue(self.state["current_issue_id"])

# 全域實例
manager = None

def get_manager():
    """取得議題管理員實例"""
    global manager
    if manager is None:
        manager = IssueManager("/root/.openclaw/workspace")
    return manager

if __name__ == "__main__":
    # 測試程式碼
    mgr = IssueManager("/root/.openclaw/workspace")
    
    # 測試建立議題
    issue_id = mgr.create_issue("測試議題", "這是測試議題的初始討論")
    print(f"建立議題: {issue_id}")
    
    # 測試更新議題
    mgr.update_issue(issue_id, "這是第一次討論內容", "第一次討論摘要")
    
    # 測試取得議題
    issue = mgr.get_issue(issue_id)
    print(f"議題內容: {json.dumps(issue, ensure_ascii=False, indent=2)}")
    
    # 測試主題偵測
    message1 = "我們來討論網站SEO優化"
    message2 = "關於資料庫設計的問題"
    
    change1, topic1 = mgr.detect_topic_change(message1)
    print(f"訊息1 - 主題轉換: {change1}, 建議標題: {topic1}")
    
    change2, topic2 = mgr.detect_topic_change(message2)
    print(f"訊息2 - 主題轉換: {change2}, 建議標題: {topic2}")