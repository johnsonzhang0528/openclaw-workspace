#!/usr/bin/env python3
"""
Telegram 介面處理器
"""

import json
import logging
from typing import Dict, List, Any, Optional
from marketplace import get_marketplace

logger = logging.getLogger(__name__)

class TelegramSkillsHandler:
    def __init__(self):
        self.marketplace = get_marketplace()
        
    def handle_command(self, command: str, args: List[str] = None) -> Dict[str, Any]:
        """處理 Telegram 命令"""
        logger.info(f"處理命令: {command}, 參數: {args}")
        
        if command == "/skills":
            return self.show_main_menu()
        elif command == "/skill_search":
            query = " ".join(args) if args else ""
            return self.search_skills(query)
        elif command == "/skill_install":
            slug = args[0] if args else ""
            return self.install_skill(slug)
        elif command == "/skill_list":
            return self.list_installed_skills()
        elif command == "/skill_update":
            slug = args[0] if args else None
            return self.update_skill(slug)
        else:
            return self.show_main_menu()
    
    def handle_callback(self, callback_data: str) -> Dict[str, Any]:
        """處理 callback 數據"""
        logger.info(f"處理 callback: {callback_data}")
        
        if callback_data.startswith("skill_install:"):
            slug = callback_data.split(":", 1)[1]
            return self.install_skill(slug)
        elif callback_data.startswith("skill_info:"):
            slug = callback_data.split(":", 1)[1]
            return self.show_skill_info(slug)
        elif callback_data == "action:search":
            return self.show_search_prompt()
        elif callback_data == "action:refresh":
            return self.show_main_menu(refresh=True)
        elif callback_data == "action:list_installed":
            return self.list_installed_skills()
        elif callback_data == "action:explore_latest":
            return self.explore_latest_skills()
        elif callback_data == "action:main_menu":
            return self.show_main_menu()
        else:
            return {"error": f"未知的 callback: {callback_data}"}
    
    def show_main_menu(self, refresh: bool = False) -> Dict[str, Any]:
        """顯示主選單"""
        message = "*🎯 技能市集*\n\n"
        message += "選擇一個操作：\n\n"
        message += "• 🔍 搜索技能\n"
        message += "• ⭐ 瀏覽最新\n"
        message += "• 📦 已安裝技能\n"
        message += "• 🔄 檢查更新\n"
        
        keyboard = [
            [
                {"text": "🔍 搜索", "callback_data": "action:search"},
                {"text": "⭐ 最新", "callback_data": "action:explore_latest"}
            ],
            [
                {"text": "📦 已安裝", "callback_data": "action:list_installed"},
                {"text": "🔄 更新", "callback_data": "action:refresh"}
            ]
        ]
        
        return {
            "message": message,
            "keyboard": keyboard,
            "parse_mode": "Markdown"
        }
    
    def search_skills(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """搜索技能"""
        if not query:
            return self.show_search_prompt()
        
        skills = self.marketplace.search_skills(query, limit)
        
        if "error" in skills[0]:
            return {
                "message": f"*🔍 搜索失敗*\n\n❌ {skills[0]['error']}",
                "parse_mode": "Markdown"
            }
        
        if not skills:
            message = f"*🔍 搜索結果: '{query}'*\n\n"
            message += "📭 沒有找到相關技能\n\n"
            message += "嘗試其他關鍵字或瀏覽最新技能。"
            
            keyboard = [
                [{"text": "🔄 重新搜索", "callback_data": "action:search"}],
                [{"text": "⭐ 瀏覽最新", "callback_data": "action:explore_latest"}],
                [{"text": "🏠 主選單", "callback_data": "action:main_menu"}]
            ]
            
            return {
                "message": message,
                "keyboard": keyboard,
                "parse_mode": "Markdown"
            }
        
        message = self.marketplace.format_for_telegram(skills, f"🔍 搜索結果: '{query}'")
        keyboard = self.marketplace.create_inline_keyboard(skills, "install")
        
        # 添加導航按鈕
        keyboard.append([
            {"text": "🔄 重新搜索", "callback_data": "action:search"},
            {"text": "🏠 主選單", "callback_data": "action:main_menu"}
        ])
        
        return {
            "message": message,
            "keyboard": keyboard,
            "parse_mode": "Markdown"
        }
    
    def show_search_prompt(self) -> Dict[str, Any]:
        """顯示搜索提示"""
        message = "*🔍 搜索技能*\n\n"
        message += "請輸入搜索關鍵字：\n"
        message += "例如：`weather`, `database`, `ai`\n\n"
        message += "或點擊按鈕瀏覽最新技能。"
        
        keyboard = [
            [{"text": "⭐ 瀏覽最新", "callback_data": "action:explore_latest"}],
            [{"text": "🏠 主選單", "callback_data": "action:main_menu"}]
        ]
        
        return {
            "message": message,
            "keyboard": keyboard,
            "parse_mode": "Markdown"
        }
    
    def explore_latest_skills(self, limit: int = 10) -> Dict[str, Any]:
        """瀏覽最新技能"""
        skills = self.marketplace.explore_latest(limit)
        
        if "error" in skills[0]:
            return {
                "message": f"*⭐ 最新技能*\n\n❌ {skills[0]['error']}",
                "parse_mode": "Markdown"
            }
        
        if not skills:
            message = "*⭐ 最新技能*\n\n"
            message += "📭 暫時沒有可用的技能\n\n"
            message += "請稍後再試或搜索其他技能。"
            
            keyboard = [
                [{"text": "🔍 搜索", "callback_data": "action:search"}],
                [{"text": "🏠 主選單", "callback_data": "action:main_menu"}]
            ]
            
            return {
                "message": message,
                "keyboard": keyboard,
                "parse_mode": "Markdown"
            }
        
        message = self.marketplace.format_for_telegram(skills, "⭐ 最新技能")
        keyboard = self.marketplace.create_inline_keyboard(skills, "install")
        
        # 添加導航按鈕
        keyboard.append([
            {"text": "🔄 刷新", "callback_data": "action:explore_latest"},
            {"text": "🏠 主選單", "callback_data": "action:main_menu"}
        ])
        
        return {
            "message": message,
            "keyboard": keyboard,
            "parse_mode": "Markdown"
        }
    
    def list_installed_skills(self) -> Dict[str, Any]:
        """列出已安裝技能"""
        skills = self.marketplace.list_installed()
        
        # 檢查錯誤
        if skills and "error" in skills[0]:
            return {
                "message": f"*📦 已安裝技能*\n\n❌ {skills[0]['error']}",
                "parse_mode": "Markdown"
            }
        
        if not skills:
            message = "*📦 已安裝技能*\n\n"
            message += "📭 尚未安裝任何技能\n\n"
            message += "點擊按鈕瀏覽並安裝技能。"
            
            keyboard = [
                [{"text": "🔍 搜索技能", "callback_data": "action:search"}],
                [{"text": "⭐ 瀏覽最新", "callback_data": "action:explore_latest"}],
                [{"text": "🏠 主選單", "callback_data": "action:main_menu"}]
            ]
            
            return {
                "message": message,
                "keyboard": keyboard,
                "parse_mode": "Markdown"
            }
        
        message = self.marketplace.format_for_telegram(skills, "📦 已安裝技能")
        
        keyboard = [
            [{"text": "🔄 檢查更新", "callback_data": "action:refresh"}],
            [{"text": "🔍 安裝更多", "callback_data": "action:search"}],
            [{"text": "🏠 主選單", "callback_data": "action:main_menu"}]
        ]
        
        return {
            "message": message,
            "keyboard": keyboard,
            "parse_mode": "Markdown"
        }
    
    def install_skill(self, slug: str) -> Dict[str, Any]:
        """安裝技能"""
        if not slug:
            return {
                "message": "*📦 安裝技能*\n\n❌ 請提供技能名稱",
                "parse_mode": "Markdown"
            }
        
        result = self.marketplace.install_skill(slug)
        
        if result["success"]:
            message = f"*✅ 安裝成功*\n\n"
            message += f"技能 `{slug}` 已成功安裝！\n\n"
            message += "現在你可以使用這個技能了。\n"
            message += "可能需要重啟 OpenClaw 或重新載入技能。"
            
            keyboard = [
                [{"text": "📦 查看已安裝", "callback_data": "action:list_installed"}],
                [{"text": "🔍 安裝更多", "callback_data": "action:search"}],
                [{"text": "🏠 主選單", "callback_data": "action:main_menu"}]
            ]
        else:
            message = f"*❌ 安裝失敗*\n\n"
            message += f"技能 `{slug}` 安裝失敗：\n"
            message += f"`{result.get('error', '未知錯誤')}`\n\n"
            message += "請檢查技能名稱或稍後再試。"
            
            keyboard = [
                [{"text": "🔄 重試", "callback_data": f"skill_install:{slug}"}],
                [{"text": "🔍 瀏覽其他", "callback_data": "action:search"}],
                [{"text": "🏠 主選單", "callback_data": "action:main_menu"}]
            ]
        
        return {
            "message": message,
            "keyboard": keyboard,
            "parse_mode": "Markdown"
        }
    
    def update_skill(self, slug: Optional[str] = None) -> Dict[str, Any]:
        """更新技能"""
        result = self.marketplace.update_skill(slug)
        
        if result["success"]:
            if slug:
                message = f"*✅ 更新成功*\n\n技能 `{slug}` 已更新。"
            else:
                message = "*✅ 更新成功*\n\n所有技能已更新。"
        else:
            if slug:
                message = f"*❌ 更新失敗*\n\n技能 `{slug}` 更新失敗：\n`{result.get('error')}`"
            else:
                message = f"*❌ 更新失敗*\n\n技能更新失敗：\n`{result.get('error')}`"
        
        keyboard = [
            [{"text": "📦 已安裝列表", "callback_data": "action:list_installed"}],
            [{"text": "🏠 主選單", "callback_data": "action:main_menu"}]
        ]
        
        return {
            "message": message,
            "keyboard": keyboard,
            "parse_mode": "Markdown"
        }
    
    def show_skill_info(self, slug: str) -> Dict[str, Any]:
        """顯示技能詳細資訊"""
        result = self.marketplace.get_skill_info(slug)
        
        if not result["success"]:
            message = f"*📋 技能資訊*\n\n❌ 無法獲取技能 `{slug}` 的資訊"
            keyboard = [[{"text": "🔙 返回", "callback_data": "action:main_menu"}]]
        else:
            info = result["info"]
            message = f"*📋 技能資訊: {slug}*\n\n"
            
            for key, value in info.items():
                if key not in ["slug", "success"]:
                    message += f"*{key}:* {value}\n"
            
            message += f"\n*安裝指令:*\n`/skill_install {slug}`"
            
            keyboard = [
                [{"text": "📦 安裝", "callback_data": f"skill_install:{slug}"}],
                [{"text": "🔙 返回", "callback_data": "action:main_menu"}]
            ]
        
        return {
            "message": message,
            "keyboard": keyboard,
            "parse_mode": "Markdown"
        }

# 單例實例
_telegram_handler_instance = None

def get_telegram_handler() -> TelegramSkillsHandler:
    """獲取 Telegram 處理器實例"""
    global _telegram_handler_instance
    if _telegram_handler_instance is None:
        _telegram_handler_instance = TelegramSkillsHandler()
    return _telegram_handler_instance

if __name__ == "__main__":
    # 測試功能
    handler = get_telegram_handler()
    
    print("=== Telegram 處理器測試 ===\n")
    
    # 測試主選單
    print("測試主選單:")
    result = handler.show_main_menu()
    print(f"訊息:\n{result['message']}")
    print(f"\n鍵盤: {json.dumps(result['keyboard'], indent=2, ensure_ascii=False)}")
    
    print("\n" + "="*50 + "\n")
    
    # 測試搜索
    print("測試搜索 'weather':")
    result = handler.search_skills("weather", limit=3)
    print(f"訊息:\n{result['message']}")
    
    print("\n" + "="*50 + "\n")
    
    # 測試最新技能
    print("測試最新技能:")
    result = handler.explore_latest_skills(limit=3)
    print(f"訊息:\n{result['message']}")