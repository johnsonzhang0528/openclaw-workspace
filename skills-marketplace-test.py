#!/usr/bin/env python3
"""
技能市集測試腳本 - Telegram 介面
"""

import subprocess
import json
import sys
from typing import List, Dict, Any

class SkillsMarketplace:
    def __init__(self):
        self.workdir = "/root/.openclaw/workspace"
        
    def run_clawhub(self, args: List[str]) -> Dict[str, Any]:
        """執行 clawhub 命令並解析結果"""
        try:
            cmd = ["clawhub", "--workdir", self.workdir] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {"error": result.stderr.strip()}
            
            return {"output": result.stdout.strip(), "success": True}
        except subprocess.TimeoutExpired:
            return {"error": "命令執行超時"}
        except Exception as e:
            return {"error": str(e)}
    
    def search_skills(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """搜索技能"""
        result = self.run_clawhub(["search", query, "--limit", str(limit)])
        
        if "error" in result:
            return [{"error": result["error"]}]
        
        skills = []
        lines = result["output"].split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith("- Searching"):
                parts = line.split('  ', 2)
                if len(parts) >= 3:
                    skills.append({
                        "slug": parts[0].split()[0],
                        "version": parts[0].split()[1] if len(parts[0].split()) > 1 else "",
                        "name": parts[1].strip(),
                        "description": parts[2].strip() if len(parts) > 2 else ""
                    })
        
        return skills
    
    def explore_latest(self, limit: int = 10) -> List[Dict[str, str]]:
        """探索最新技能"""
        result = self.run_clawhub(["explore", "--limit", str(limit)])
        
        if "error" in result:
            return [{"error": result["error"]}]
        
        skills = []
        lines = result["output"].split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith("- Fetching"):
                parts = line.split('  ', 3)
                if len(parts) >= 4:
                    skills.append({
                        "slug": parts[0],
                        "version": parts[1],
                        "updated": parts[2],
                        "description": parts[3].strip()
                    })
        
        return skills
    
    def list_installed(self) -> List[Dict[str, str]]:
        """列出已安裝技能"""
        result = self.run_clawhub(["list"])
        
        if "error" in result:
            return [{"error": result["error"]}]
        
        if "No installed skills" in result["output"]:
            return []
        
        skills = []
        lines = result["output"].split('\n')
        
        for line in lines:
            if line.strip():
                skills.append({"name": line.strip()})
        
        return skills
    
    def install_skill(self, slug: str) -> Dict[str, Any]:
        """安裝技能"""
        return self.run_clawhub(["install", slug])
    
    def update_skill(self, slug: str = None) -> Dict[str, Any]:
        """更新技能"""
        if slug:
            return self.run_clawhub(["update", slug])
        else:
            return self.run_clawhub(["update", "--all"])
    
    def format_telegram_message(self, skills: List[Dict[str, str]], title: str) -> str:
        """格式化 Telegram 訊息"""
        if not skills:
            return f"*{title}*\n\n📭 沒有找到技能"
        
        if "error" in skills[0]:
            return f"*{title}*\n\n❌ 錯誤：{skills[0]['error']}"
        
        message = f"*{title}*\n\n"
        
        for i, skill in enumerate(skills, 1):
            if "slug" in skill:
                message += f"{i}. *{skill.get('name', skill['slug'])}*"
                if "version" in skill:
                    message += f" v{skill['version']}"
                if "updated" in skill:
                    message += f" ({skill['updated']})"
                if "description" in skill:
                    message += f"\n   {skill['description']}"
                message += f"\n   `{skill['slug']}`\n\n"
            elif "name" in skill:
                message += f"• {skill['name']}\n"
        
        return message
    
    def create_inline_keyboard(self, skills: List[Dict[str, str]], action: str = "install") -> List[List[Dict[str, str]]]:
        """創建 inline keyboard 按鈕"""
        keyboard = []
        
        for skill in skills:
            if "slug" in skill:
                keyboard.append([{
                    "text": f"📦 {skill.get('name', skill['slug'])}",
                    "callback_data": f"{action}:{skill['slug']}"
                }])
        
        # 添加導航按鈕
        if action == "install":
            keyboard.append([
                {"text": "🔍 搜索更多", "callback_data": "action:search"},
                {"text": "🔄 刷新列表", "callback_data": "action:refresh"}
            ])
        
        return keyboard

def main():
    """主函數 - 測試功能"""
    marketplace = SkillsMarketplace()
    
    print("=== 技能市集測試 ===\n")
    
    # 測試搜索功能
    print("1. 搜索 'weather' 相關技能：")
    weather_skills = marketplace.search_skills("weather", limit=3)
    print(marketplace.format_telegram_message(weather_skills, "天氣相關技能"))
    
    print("\n" + "="*50 + "\n")
    
    # 測試探索最新功能
    print("2. 最新技能：")
    latest_skills = marketplace.explore_latest(limit=3)
    print(marketplace.format_telegram_message(latest_skills, "最新技能"))
    
    print("\n" + "="*50 + "\n")
    
    # 測試已安裝列表
    print("3. 已安裝技能：")
    installed_skills = marketplace.list_installed()
    print(marketplace.format_telegram_message(installed_skills, "已安裝技能"))
    
    print("\n" + "="*50 + "\n")
    
    # 測試 inline keyboard
    print("4. Inline Keyboard 範例：")
    keyboard = marketplace.create_inline_keyboard(weather_skills[:2], "install")
    print(json.dumps(keyboard, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()