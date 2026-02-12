#!/usr/bin/env python3
"""
技能市集瀏覽器 - 瀏覽和安裝第三方技能
"""

import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

class SkillMarketplace:
    def __init__(self):
        self.base_dir = Path.home() / ".openclaw"
        self.skills_dir = self.base_dir / "skills" / "marketplace"
        self.installed_file = self.skills_dir / "installed.json"
        self.registry_file = self.skills_dir / "cache" / "registry.json"
        
        # 確保目錄存在
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        (self.skills_dir / "cache").mkdir(exist_ok=True)
        
        # 加載數據
        self.installed_skills = self._load_json(self.installed_file, {"installed_skills": []})
        self.registry = self._load_json(self.registry_file, {"skills": [], "categories": {}})
    
    def _load_json(self, filepath, default=None):
        """加載 JSON 文件"""
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"加載 {filepath} 時出錯: {e}")
        return default if default is not None else {}
    
    def _save_json(self, filepath, data):
        """保存 JSON 文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"保存 {filepath} 時出錯: {e}")
            return False
    
    def sync_registry(self, force=False):
        """同步技能註冊表"""
        cache_file = self.skills_dir / "cache" / "registry.json"
        
        # 檢查緩存是否過期（24小時）
        if not force and cache_file.exists():
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime < 86400:  # 24小時
                print("使用緩存的技能註冊表")
                return True
        
        print("同步技能註冊表...")
        
        # 這裡可以從遠程服務器獲取技能列表
        # 暫時使用示例數據
        example_skills = [
            {
                "id": "file-manager",
                "name": "文件管理器",
                "version": "1.0.0",
                "description": "高級文件管理工具",
                "author": "OpenClaw Team",
                "repository": "https://github.com/openclaw/skill-file-manager",
                "dependencies": [],
                "tags": ["file", "management", "productivity"],
                "category": "productivity"
            },
            {
                "id": "network-monitor",
                "name": "網絡監控",
                "version": "1.0.0",
                "description": "實時網絡監控工具",
                "author": "OpenClaw Team",
                "repository": "https://github.com/openclaw/skill-network-monitor",
                "dependencies": [],
                "tags": ["network", "monitoring", "system"],
                "category": "system"
            },
            {
                "id": "weather-forecast",
                "name": "天氣預報",
                "version": "1.0.0",
                "description": "實時天氣信息和預報",
                "author": "OpenClaw Team",
                "repository": "https://github.com/openclaw/skill-weather",
                "dependencies": [],
                "tags": ["weather", "forecast", "utilities"],
                "category": "utilities"
            }
        ]
        
        self.registry = {
            "version": "1.0.0",
            "last_sync": datetime.now().isoformat(),
            "skills": example_skills,
            "categories": {
                "productivity": "生產力工具",
                "system": "系統工具",
                "utilities": "實用工具",
                "development": "開發工具",
                "communication": "通訊"
            }
        }
        
        return self._save_json(cache_file, self.registry)
    
    def list_skills(self, category=None, search=None):
        """列出技能"""
        skills = self.registry.get("skills", [])
        
        # 過濾分類
        if category:
            skills = [s for s in skills if s.get("category") == category]
        
        # 搜索
        if search:
            search_lower = search.lower()
            skills = [
                s for s in skills 
                if search_lower in s.get("name", "").lower() 
                or search_lower in s.get("description", "").lower()
                or any(search_lower in tag.lower() for tag in s.get("tags", []))
            ]
        
        return skills
    
    def get_skill_info(self, skill_id):
        """獲取技能詳細信息"""
        for skill in self.registry.get("skills", []):
            if skill.get("id") == skill_id:
                return skill
        return None
    
    def install_skill(self, skill_id):
        """安裝技能"""
        skill = self.get_skill_info(skill_id)
        if not skill:
            print(f"找不到技能: {skill_id}")
            return False
        
        # 檢查是否已安裝
        installed_ids = [s.get("id") for s in self.installed_skills.get("installed_skills", [])]
        if skill_id in installed_ids:
            print(f"技能已安裝: {skill_id}")
            return True
        
        print(f"安裝技能: {skill['name']}")
        
        # 這裡實現實際的安裝邏輯
        # 例如：使用 openclaw skills 命令或直接從倉庫安裝
        
        # 添加到已安裝列表
        self.installed_skills.setdefault("installed_skills", []).append({
            **skill,
            "installed_at": datetime.now().isoformat(),
            "enabled": True
        })
        
        # 更新最後更新時間
        self.installed_skills["last_updated"] = datetime.now().isoformat()
        
        # 保存
        if self._save_json(self.installed_file, self.installed_skills):
            print(f"成功安裝: {skill['name']}")
            return True
        else:
            print(f"安裝失敗: {skill['name']}")
            return False
    
    def uninstall_skill(self, skill_id):
        """卸載技能"""
        # 從已安裝列表中移除
        original_count = len(self.installed_skills.get("installed_skills", []))
        self.installed_skills["installed_skills"] = [
            s for s in self.installed_skills.get("installed_skills", [])
            if s.get("id") != skill_id
        ]
        
        if len(self.installed_skills["installed_skills"]) < original_count:
            self.installed_skills["last_updated"] = datetime.now().isoformat()
            if self._save_json(self.installed_file, self.installed_skills):
                print(f"成功卸載技能: {skill_id}")
                return True
        
        print(f"技能未安裝: {skill_id}")
        return False
    
    def list_installed(self):
        """列出已安裝技能"""
        return self.installed_skills.get("installed_skills", [])
    
    def update_skill(self, skill_id):
        """更新技能"""
        print(f"更新技能: {skill_id}")
        # 這裡實現更新邏輯
        return True
    
    def get_categories(self):
        """獲取分類列表"""
        return self.registry.get("categories", {})

def main():
    """主函數"""
    marketplace = SkillMarketplace()
    
    # 同步註冊表
    marketplace.sync_registry()
    
    # 示例：列出所有技能
    print("可用技能:")
    skills = marketplace.list_skills()
    for i, skill in enumerate(skills, 1):
        print(f"{i}. {skill['name']} - {skill['description']}")
    
    # 示例：安裝一個技能
    if skills:
        marketplace.install_skill(skills[0]["id"])
    
    # 列出已安裝技能
    print("\n已安裝技能:")
    installed = marketplace.list_installed()
    for skill in installed:
        print(f"- {skill['name']} ({skill.get('installed_at', '未知時間')})")

if __name__ == "__main__":
    main()