#!/usr/bin/env python3
"""
技能市集瀏覽器 - 主程式
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional

# 添加技能目錄到路徑
skill_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, skill_dir)

from config import SkillConfig
from telegram_ui import TelegramUI
import utils

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SkillsMarketplaceSkill:
    """技能市集瀏覽器主類別"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化技能"""
        self.config = SkillConfig(config_path)
        self.telegram_ui = TelegramUI(self.config)
        self.initialized = False
        
        logger.info(f"初始化技能市集瀏覽器 v{self.config.version}")
    
    def initialize(self) -> bool:
        """初始化技能，返回是否成功"""
        try:
            # 創建資料目錄
            os.makedirs(self.config.data_path, exist_ok=True)
            
            # 加載資料
            self._load_data()
            
            # 初始化 Telegram 介面
            if self.config.telegram_enabled:
                self.telegram_ui.initialize()
            
            self.initialized = True
            logger.info("技能市集瀏覽器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化失敗: {e}")
            return False
    
    def _load_data(self):
        """加載技能資料"""
        data_file = os.path.join(self.config.data_path, 'data.json')
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'version': self.config.version,
                'created_at': utils.get_current_timestamp(),
                'installed_skills': [],
                'catalog_cache': {},
                'last_update': None,
                'stats': {
                    'browse_count': 0,
                    'install_count': 0,
                    'search_count': 0
                }
            }
    
    def _save_data(self):
        """儲存技能資料"""
        data_file = os.path.join(self.config.data_path, 'data.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def handle_command(self, command: str, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理命令
        
        Args:
            command: 命令名稱
            args: 命令參數
            context: 上下文資訊
            
        Returns:
            回應字典
        """
        if not self.initialized:
            return {
                'success': False,
                'message': '技能未初始化',
                'error': 'NOT_INITIALIZED'
            }
        
        try:
            # 更新統計
            self.data['stats']['browse_count'] += 1
            self._save_data()
            
            # 根據命令類型處理
            if command == 'help' or command == '幫助':
                return self._handle_help(args, context)
            elif command == 'status' or command == '狀態':
                return self._handle_status(args, context)
            elif command == 'browse' or command == '瀏覽':
                return self._handle_browse(args, context)
            elif command == 'search' or command == '搜尋':
                return self._handle_search(args, context)
            elif command == 'installed' or command == '已安裝':
                return self._handle_installed(args, context)
            elif command == 'install' or command == '安裝':
                return self._handle_install(args, context)
            elif command == 'update' or command == '更新':
                return self._handle_update(args, context)
            else:
                return self._handle_main_menu(args, context)
                
        except Exception as e:
            logger.error(f"處理命令 {command} 時出錯: {e}")
            return {
                'success': False,
                'message': f'處理命令時出錯: {str(e)}',
                'error': 'COMMAND_ERROR'
            }
    
    def _handle_help(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理幫助命令"""
        help_text = f"""
技能市集瀏覽器幫助

可用命令:
• /技能市集 - 顯示主選單
• /技能市集 瀏覽 - 瀏覽所有技能
• /技能市集 搜尋 <關鍵字> - 搜尋技能
• /技能市集 已安裝 - 查看已安裝技能
• /技能市集 安裝 <技能名> - 安裝技能
• /技能市集 更新 - 檢查技能更新
• /技能市集 狀態 - 顯示技能狀態
• /技能市集 幫助 - 顯示此幫助訊息

快捷命令:
• /market - 技能市集快捷命令

使用範例:
/技能市集 搜尋 weather
/技能市集 安裝 weather
        """.strip()
        
        return {
            'success': True,
            'message': help_text,
            'format': 'text'
        }
    
    def _handle_status(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理狀態命令"""
        status = {
            'skill': '技能市集瀏覽器',
            'version': self.config.version,
            'initialized': self.initialized,
            'telegram_enabled': self.config.telegram_enabled,
            'data_path': self.config.data_path,
            'installed_count': len(self.data.get('installed_skills', [])),
            'catalog_size': len(self.data.get('catalog_cache', {})),
            'stats': self.data.get('stats', {}),
            'last_update': self.data.get('last_update')
        }
        
        status_text = f"""
技能市集狀態

• 版本: {status['version']}
• 狀態: {'已初始化' if status['initialized'] else '未初始化'}
• 已安裝技能: {status['installed_count']} 個
• 目錄快取: {status['catalog_size']} 個技能
• 瀏覽次數: {status['stats'].get('browse_count', 0)}
• 安裝次數: {status['stats'].get('install_count', 0)}
• 最後更新: {status['last_update'] or '從未更新'}
        """.strip()
        
        return {
            'success': True,
            'message': status_text,
            'data': status,
            'format': 'text'
        }
    
    def _handle_browse(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理瀏覽命令"""
        # 模擬技能目錄
        sample_skills = [
            {'name': 'weather', 'description': '天氣查詢技能', 'rating': 4.5, 'downloads': 1000},
            {'name': 'calculator', 'description': '計算器技能', 'rating': 4.2, 'downloads': 800},
            {'name': 'translator', 'description': '翻譯技能', 'rating': 4.7, 'downloads': 1200},
            {'name': 'news', 'description': '新聞閱讀技能', 'rating': 4.3, 'downloads': 900},
            {'name': 'reminder', 'description': '提醒事項技能', 'rating': 4.6, 'downloads': 1100},
        ]
        
        browse_text = "📚 可用技能列表:\n\n"
        for i, skill in enumerate(sample_skills, 1):
            browse_text += f"{i}. **{skill['name']}**\n"
            browse_text += f"   📝 {skill['description']}\n"
            browse_text += f"   ⭐ {skill['rating']}/5.0 | 📥 {skill['downloads']} 次下載\n\n"
        
        browse_text += "使用 `/技能市集 安裝 <技能名>` 安裝技能"
        
        return {
            'success': True,
            'message': browse_text,
            'data': sample_skills,
            'format': 'text'
        }
    
    def _handle_search(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理搜尋命令"""
        if not args:
            return {
                'success': False,
                'message': '請提供搜尋關鍵字，例如: /技能市集 搜尋 weather',
                'format': 'text'
            }
        
        keyword = args[0].lower()
        self.data['stats']['search_count'] += 1
        self._save_data()
        
        # 模擬搜尋結果
        all_skills = [
            {'name': 'weather', 'description': '天氣查詢技能', 'category': 'utility'},
            {'name': 'calculator', 'description': '計算器技能', 'category': 'utility'},
            {'name': 'translator', 'description': '翻譯技能', 'category': 'language'},
            {'name': 'news', 'description': '新聞閱讀技能', 'category': 'news'},
            {'name': 'reminder', 'description': '提醒事項技能', 'category': 'productivity'},
        ]
        
        results = []
        for skill in all_skills:
            if (keyword in skill['name'].lower() or 
                keyword in skill['description'].lower() or
                keyword in skill['category'].lower()):
                results.append(skill)
        
        if not results:
            search_text = f"🔍 未找到包含「{keyword}」的技能"
        else:
            search_text = f"🔍 搜尋「{keyword}」找到 {len(results)} 個結果:\n\n"
            for i, skill in enumerate(results, 1):
                search_text += f"{i}. **{skill['name']}**\n"
                search_text += f"   📝 {skill['description']}\n"
                search_text += f"   🏷️  {skill['category']}\n\n"
        
        return {
            'success': True,
            'message': search_text,
            'data': results,
            'format': 'text'
        }
    
    def _handle_installed(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理已安裝命令"""
        installed_skills = self.data.get('installed_skills', [])
        
        if not installed_skills:
            installed_text = "📦 尚未安裝任何技能\n\n使用 `/技能市集 瀏覽` 查看可用技能"
        else:
            installed_text = f"📦 已安裝 {len(installed_skills)} 個技能:\n\n"
            for i, skill in enumerate(installed_skills, 1):
                installed_text += f"{i}. **{skill.get('name', '未知技能')}**\n"
                if 'version' in skill:
                    installed_text += f"   版本: {skill['version']}\n"
                if 'installed_at' in skill:
                    installed_text += f"   安裝時間: {skill['installed_at']}\n"
                installed_text += "\n"
        
        return {
            'success': True,
            'message': installed_text,
            'data': installed_skills,
            'format': 'text'
        }
    
    def _handle_install(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理安裝命令"""
        if not args:
            return {
                'success': False,
                'message': '請提供技能名稱，例如: /技能市集 安裝 weather',
                'format': 'text'
            }
        
        skill_name = args[0].lower()
        
        # 檢查是否已安裝
        installed_skills = self.data.get('installed_skills', [])
        for skill in installed_skills:
            if skill.get('name') == skill_name:
                return {
                    'success': False,
                    'message': f'技能「{skill_name}」已經安裝',
                    'format': 'text'
                }
        
        # 模擬安裝
        new_skill = {
            'name': skill_name,
            'version': '1.0.0',
            'installed_at': utils.get_current_timestamp(),
            'status': 'active'
        }
        
        installed_skills.append(new_skill)
        self.data['installed_skills'] = installed_skills
        self.data['stats']['install_count'] += 1
        self._save_data()
        
        install_text = f"✅ 成功安裝技能「{skill_name}」\n\n"
        install_text += f"版本: 1.0.0\n"
        install_text += f"安裝時間: {new_skill['installed_at']}\n\n"
        install_text += "使用 `/技能市集 已安裝` 查看所有已安裝技能"
        
        return {
            'success': True,
            'message': install_text,
            'data': new_skill,
            'format': 'text'
        }
    
    def _handle_update(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理更新命令"""
        # 模擬更新檢查
        self.data['last_update'] = utils.get_current_timestamp()
        self._save_data()
        
        update_text = "🔄 正在檢查技能更新...\n\n"
        update_text += "✅ 技能目錄已更新\n"
        update_text += f"📅 更新時間: {self.data['last_update']}\n\n"
        update_text += "所有技能都是最新版本！"
        
        return {
            'success': True,
            'message': update_text,
            'format': 'text'
        }
    
    def _handle_main_menu(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理主選單命令"""
        menu_text = """
🛒 技能市集瀏覽器

選擇操作:
• 🔍 瀏覽技能 - 查看所有可用技能
• 🔎 搜尋技能 - 搜尋特定技能
• 📦 已安裝技能 - 查看已安裝技能
• ⬇️ 安裝技能 - 安裝新技能
• 🔄 檢查更新 - 更新技能目錄
• 📊 狀態資訊 - 查看市集狀態
• ❓ 幫助 - 顯示幫助訊息

使用範例:
/技能市集 瀏覽
/技能市集 搜尋 weather
/技能市集 安裝 calculator
        """.strip()
        
        return {
            'success': True,
            'message': menu_text,
            'format': 'text',
            'buttons': [
                [{'text': '🔍 瀏覽技能', 'callback_data': 'browse'}],
                [{'text': '🔎 搜尋技能', 'callback_data': 'search'}],
                [{'text': '📦 已安裝', 'callback_data': 'installed'}],
                [{'text': '⬇️ 安裝技能', 'callback_data': 'install'}],
                [{'text': '🔄 檢查更新', 'callback_data': 'update'}],
                [{'text': '📊 狀態', 'callback_data': 'status'}],
                [{'text': '❓ 幫助', 'callback_data': 'help'}]
            ]
        }
    
    def cleanup(self):
        """清理資源"""
        if self.initialized:
            self._save_data()
            logger.info("技能市集瀏覽器清理完成")
    
    def __del__(self):
        """解構函數"""
        self.cleanup()


def main():
    """主函數（用於獨立測試）"""
    skill = SkillsMarketplaceSkill()
    
    if skill.initialize():
        print("技能初始化成功")
        
        # 測試命令處理
        test_context = {
            'user_id': 'test_user',
            'chat_id': 'test_chat',
            'platform': 'cli'
        }
        
        result = skill.handle_command('status', [], test_context)
        print(f"狀態檢查: {result}")
        
        result = skill.handle_command('browse', [], test_context)
        print(f"瀏覽技能: {len(result.get('data', []))} 個技能")
        
        skill.cleanup()
    else:
        print("技能初始化失敗")


if __name__ == '__main__':
    main()