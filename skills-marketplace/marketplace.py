#!/usr/bin/env python3
"""
技能市集主程式
"""

import os
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/.openclaw/logs/skills-marketplace.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SkillsMarketplace:
    def __init__(self, workdir: str = "/root/.openclaw/workspace"):
        self.workdir = workdir
        self.skills_dir = os.path.join(workdir, "skills-marketplace")
        self.data_dir = os.path.join(self.skills_dir, "data")
        
        # 建立目錄
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 資料檔案路徑
        self.installed_file = os.path.join(self.data_dir, "installed_skills.json")
        self.catalog_file = os.path.join(self.data_dir, "catalog_cache.json")
        self.prefs_file = os.path.join(self.data_dir, "user_preferences.json")
        
        # 初始化資料
        self._init_data()
        
    def _init_data(self):
        """初始化資料檔案"""
        defaults = {
            self.installed_file: {"installed": [], "last_updated": None},
            self.catalog_file: {"skills": [], "last_sync": None},
            self.prefs_file: {"preferences": {}, "favorites": []}
        }
        
        for file_path, default_data in defaults.items():
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
    
    def _load_json(self, file_path: str) -> Dict:
        """載入 JSON 檔案"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_json(self, file_path: str, data: Dict):
        """儲存 JSON 檔案"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def run_clawhub(self, args: List[str]) -> Dict[str, Any]:
        """執行 clawhub 命令"""
        try:
            cmd = ["clawhub", "--workdir", self.workdir] + args
            logger.info(f"執行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60,
                cwd=self.workdir
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "未知錯誤"
                logger.error(f"命令失敗: {error_msg}")
                return {"success": False, "error": error_msg}
            
            logger.info("命令執行成功")
            return {"success": True, "output": result.stdout.strip()}
            
        except subprocess.TimeoutExpired:
            error_msg = "命令執行超時"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"執行錯誤: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def search_skills(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """搜索技能"""
        logger.info(f"搜索技能: {query}")
        
        result = self.run_clawhub(["search", query, "--limit", str(limit)])
        
        if not result["success"]:
            return [{"error": result["error"]}]
        
        skills = []
        lines = result["output"].split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith("- Searching"):
                # 解析格式: slug version name description
                parts = [p.strip() for p in line.split('  ') if p.strip()]
                
                if len(parts) >= 3:
                    slug_version = parts[0].split()
                    slug = slug_version[0] if slug_version else ""
                    version = slug_version[1] if len(slug_version) > 1 else ""
                    
                    skill = {
                        "slug": slug,
                        "version": version,
                        "name": parts[1],
                        "description": parts[2] if len(parts) > 2 else "",
                        "score": parts[3] if len(parts) > 3 else "0.0"
                    }
                    skills.append(skill)
        
        # 更新快取
        if skills:
            self._update_catalog_cache(skills)
        
        return skills
    
    def explore_latest(self, limit: int = 10) -> List[Dict[str, str]]:
        """探索最新技能"""
        logger.info(f"探索最新技能，限制: {limit}")
        
        result = self.run_clawhub(["explore", "--limit", str(limit)])
        
        if not result["success"]:
            return [{"error": result["error"]}]
        
        skills = []
        lines = result["output"].split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith("- Fetching"):
                # 解析格式: slug version updated description
                parts = [p.strip() for p in line.split('  ') if p.strip()]
                
                if len(parts) >= 4:
                    skill = {
                        "slug": parts[0],
                        "version": parts[1],
                        "updated": parts[2],
                        "description": parts[3]
                    }
                    skills.append(skill)
        
        return skills
    
    def list_installed(self) -> List[Dict[str, str]]:
        """列出已安裝技能"""
        logger.info("列出已安裝技能")
        
        # 從 clawhub 獲取
        result = self.run_clawhub(["list"])
        
        installed_skills = []
        
        if result["success"]:
            lines = result["output"].split('\n')
            for line in lines:
                line = line.strip()
                if line and line != "No installed skills.":
                    installed_skills.append({"name": line})
        
        # 從本地檔案獲取
        local_data = self._load_json(self.installed_file)
        local_installed = local_data.get("installed", [])
        
        # 合併結果
        all_skills = []
        skill_names = set()
        
        for skill in installed_skills + local_installed:
            name = skill.get("name") or skill.get("slug", "")
            if name and name not in skill_names:
                skill_names.add(name)
                all_skills.append(skill)
        
        return all_skills
    
    def install_skill(self, slug: str) -> Dict[str, Any]:
        """安裝技能"""
        logger.info(f"安裝技能: {slug}")
        
        result = self.run_clawhub(["install", slug])
        
        if result["success"]:
            # 更新已安裝列表
            installed_data = self._load_json(self.installed_file)
            installed_list = installed_data.get("installed", [])
            
            # 檢查是否已存在
            if not any(s.get("slug") == slug for s in installed_list):
                installed_list.append({
                    "slug": slug,
                    "installed_at": datetime.now().isoformat(),
                    "status": "installed"
                })
                installed_data["installed"] = installed_list
                installed_data["last_updated"] = datetime.now().isoformat()
                self._save_json(self.installed_file, installed_data)
            
            logger.info(f"技能安裝成功: {slug}")
            return {"success": True, "message": f"技能 '{slug}' 安裝成功"}
        else:
            logger.error(f"技能安裝失敗: {slug} - {result.get('error')}")
            return {"success": False, "error": result.get("error", "安裝失敗")}
    
    def update_skill(self, slug: Optional[str] = None) -> Dict[str, Any]:
        """更新技能"""
        if slug:
            logger.info(f"更新技能: {slug}")
            result = self.run_clawhub(["update", slug])
        else:
            logger.info("更新所有技能")
            result = self.run_clawhub(["update", "--all"])
        
        if result["success"]:
            message = f"技能 '{slug}' 更新成功" if slug else "所有技能更新成功"
            logger.info(message)
            return {"success": True, "message": message}
        else:
            error = result.get("error", "更新失敗")
            logger.error(f"更新失敗: {error}")
            return {"success": False, "error": error}
    
    def get_skill_info(self, slug: str) -> Dict[str, Any]:
        """獲取技能詳細資訊"""
        logger.info(f"獲取技能資訊: {slug}")
        
        result = self.run_clawhub(["inspect", slug])
        
        if result["success"]:
            # 解析輸出
            info = {"slug": slug}
            lines = result["output"].split('\n')
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()
            
            return {"success": True, "info": info}
        else:
            return {"success": False, "error": result.get("error", "獲取資訊失敗")}
    
    def _update_catalog_cache(self, skills: List[Dict]):
        """更新目錄快取"""
        try:
            cache_data = self._load_json(self.catalog_file)
            cached_skills = cache_data.get("skills", [])
            
            # 更新或添加技能
            for skill in skills:
                slug = skill.get("slug")
                if slug:
                    # 查找是否已存在
                    existing_idx = -1
                    for i, cached in enumerate(cached_skills):
                        if cached.get("slug") == slug:
                            existing_idx = i
                            break
                    
                    if existing_idx >= 0:
                        cached_skills[existing_idx].update(skill)
                    else:
                        cached_skills.append(skill)
            
            # 限制快取大小
            if len(cached_skills) > 100:
                cached_skills = cached_skills[-100:]
            
            cache_data["skills"] = cached_skills
            cache_data["last_sync"] = datetime.now().isoformat()
            self._save_json(self.catalog_file, cache_data)
            
            logger.info(f"目錄快取已更新，共 {len(cached_skills)} 個技能")
            
        except Exception as e:
            logger.error(f"更新快取失敗: {e}")
    
    def format_for_telegram(self, skills: List[Dict], title: str) -> str:
        """格式化為 Telegram 訊息"""
        if not skills:
            return f"*{title}*\n\n📭 沒有找到技能"
        
        if "error" in skills[0]:
            return f"*{title}*\n\n❌ 錯誤：{skills[0]['error']}"
        
        message = f"*{title}*\n\n"
        
        for i, skill in enumerate(skills, 1):
            if "slug" in skill:
                # 格式化技能資訊
                name = skill.get("name", skill["slug"])
                message += f"{i}. *{name}*"
                
                if "version" in skill:
                    message += f" v{skill['version']}"
                
                if "updated" in skill:
                    message += f" ({skill['updated']})"
                
                if "description" in skill:
                    desc = skill["description"]
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    message += f"\n   {desc}"
                
                message += f"\n   `{skill['slug']}`\n\n"
            elif "name" in skill:
                message += f"• {skill['name']}\n"
        
        return message
    
    def create_inline_keyboard(self, skills: List[Dict], action: str = "install") -> List[List[Dict[str, str]]]:
        """創建 inline keyboard"""
        keyboard = []
        
        for skill in skills:
            if "slug" in skill:
                name = skill.get("name", skill["slug"])
                if len(name) > 20:
                    name = name[:17] + "..."
                
                keyboard.append([{
                    "text": f"📦 {name}",
                    "callback_data": f"skill_{action}:{skill['slug']}"
                }])
        
        # 添加操作按鈕
        if action == "install":
            keyboard.append([
                {"text": "🔍 搜索", "callback_data": "action:search"},
                {"text": "🔄 刷新", "callback_data": "action:refresh"}
            ])
            keyboard.append([
                {"text": "📋 已安裝", "callback_data": "action:list_installed"},
                {"text": "⭐ 最新", "callback_data": "action:explore_latest"}
            ])
        
        return keyboard

# 單例實例
_marketplace_instance = None

def get_marketplace() -> SkillsMarketplace:
    """獲取技能市集實例"""
    global _marketplace_instance
    if _marketplace_instance is None:
        _marketplace_instance = SkillsMarketplace()
    return _marketplace_instance

if __name__ == "__main__":
    # 測試功能
    marketplace = get_marketplace()
    
    print("=== 技能市集測試 ===\n")
    
    # 測試搜索
    print("測試搜索 'weather':")
    skills = marketplace.search_skills("weather", limit=3)
    print(marketplace.format_for_telegram(skills, "測試結果"))
    
    print("\n" + "="*50 + "\n")
    
    # 測試最新技能
    print("測試最新技能:")
    latest = marketplace.explore_latest(limit=3)
    print(marketplace.format_for_telegram(latest, "最新技能"))
    
    print("\n" + "="*50 + "\n")
    
    # 測試已安裝
    print("測試已安裝技能:")
    installed = marketplace.list_installed()
    print(marketplace.format_for_telegram(installed, "已安裝技能"))