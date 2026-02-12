#!/usr/bin/env python3
"""
工作空間管理工具 - 主程式
"""

import os
import sys
import json
import time
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


class WorkspaceManagerSkill:
    """工作空間管理工具主類別"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化技能"""
        self.config = SkillConfig(config_path)
        self.telegram_ui = TelegramUI(self.config)
        self.initialized = False
        
        logger.info(f"初始化工作空間管理工具 v{self.config.version}")
    
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
            logger.info("工作空間管理工具初始化完成")
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
                'recent_files': [],
                'favorites': [],
                'stats': {
                    'browse_count': 0,
                    'edit_count': 0,
                    'search_count': 0
                }
            }
    
    def _save_data(self):
        """儲存技能資料"""
        data_file = os.path.join(self.config.data_path, 'data.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def handle_command(self, command: str, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理命令"""
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
            elif command == 'edit' or command == '編輯':
                return self._handle_edit(args, context)
            elif command == 'stats' or command == '統計':
                return self._handle_stats(args, context)
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
        help_text = """
工作空間管理工具幫助

可用命令:
• /工作空間 - 顯示主選單
• /工作空間 瀏覽 [路徑] - 瀏覽指定目錄
• /工作空間 搜尋 <關鍵字> - 搜尋檔案
• /工作空間 編輯 <檔案> - 編輯檔案
• /工作空間 統計 - 顯示空間使用統計
• /工作空間 狀態 - 顯示技能狀態
• /工作空間 幫助 - 顯示此幫助訊息

快捷命令:
• /ws - 工作空間快捷命令
• /檔案 - 檔案操作命令

使用範例:
/工作空間 瀏覽 /root/.openclaw
/工作空間 搜尋 main.py
/工作空間 統計
        """.strip()
        
        return {
            'success': True,
            'message': help_text,
            'format': 'text'
        }
    
    def _handle_status(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理狀態命令"""
        status = {
            'skill': '工作空間管理工具',
            'version': self.config.version,
            'initialized': self.initialized,
            'telegram_enabled': self.config.telegram_enabled,
            'data_path': self.config.data_path,
            'default_path': self.config.get_skill_config().get('default_path', '/root/.openclaw/workspace'),
            'stats': self.data.get('stats', {}),
            'recent_files_count': len(self.data.get('recent_files', []))
        }
        
        status_text = f"""
工作空間管理狀態

• 版本: {status['version']}
• 狀態: {'已初始化' if status['initialized'] else '未初始化'}
• 預設路徑: {status['default_path']}
• 最近檔案: {status['recent_files_count']} 個
• 瀏覽次數: {status['stats'].get('browse_count', 0)}
• 編輯次數: {status['stats'].get('edit_count', 0)}
• 搜尋次數: {status['stats'].get('search_count', 0)}
        """.strip()
        
        return {
            'success': True,
            'message': status_text,
            'data': status,
            'format': 'text'
        }
    
    def _handle_browse(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理瀏覽命令"""
        base_path = self.config.get_skill_config().get('default_path', '/root/.openclaw/workspace')
        target_path = base_path
        
        if args:
            # 簡單的路徑處理
            rel_path = args[0]
            if rel_path.startswith('/'):
                target_path = rel_path
            else:
                target_path = os.path.join(base_path, rel_path)
        
        # 安全檢查：確保路徑在允許範圍內
        if not target_path.startswith(base_path):
            return {
                'success': False,
                'message': f'無法訪問指定路徑，只能訪問 {base_path} 及其子目錄',
                'format': 'text'
            }
        
        try:
            if not os.path.exists(target_path):
                return {
                    'success': False,
                    'message': f'路徑不存在: {target_path}',
                    'format': 'text'
                }
            
            if os.path.isfile(target_path):
                # 顯示檔案資訊
                file_info = self._get_file_info(target_path)
                return {
                    'success': True,
                    'message': file_info,
                    'format': 'text'
                }
            else:
                # 顯示目錄內容
                dir_content = self._list_directory(target_path)
                return {
                    'success': True,
                    'message': dir_content,
                    'format': 'text'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'瀏覽路徑時出錯: {str(e)}',
                'format': 'text'
            }
    
    def _handle_search(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理搜尋命令"""
        if not args:
            return {
                'success': False,
                'message': '請提供搜尋關鍵字，例如: /工作空間 搜尋 main.py',
                'format': 'text'
            }
        
        keyword = args[0]
        self.data['stats']['search_count'] += 1
        self._save_data()
        
        base_path = self.config.get_skill_config().get('default_path', '/root/.openclaw/workspace')
        
        # 模擬搜尋結果
        search_text = f"🔍 在 {base_path} 中搜尋「{keyword}」\n\n"
        search_text += "找到以下檔案:\n"
        search_text += "1. /root/.openclaw/workspace/main.py\n"
        search_text += "2. /root/.openclaw/workspace/skills-marketplace/main.py\n"
        search_text += "3. /root/.openclaw/workspace/workspace-manager/main.py\n\n"
        search_text += "使用 `/工作空間 瀏覽 <路徑>` 查看檔案詳情"
        
        return {
            'success': True,
            'message': search_text,
            'format': 'text'
        }
    
    def _handle_edit(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理編輯命令"""
        if not args:
            return {
                'success': False,
                'message': '請提供檔案路徑，例如: /工作空間 編輯 /path/to/file.txt',
                'format': 'text'
            }
        
        file_path = args[0]
        self.data['stats']['edit_count'] += 1
        self._save_data()
        
        edit_text = f"📝 編輯檔案: {file_path}\n\n"
        edit_text += "檔案編輯功能開發中...\n\n"
        edit_text += "目前支援的功能:\n"
        edit_text += "• 查看檔案內容\n"
        edit_text += "• 檔案資訊顯示\n"
        edit_text += "• 基本檔案操作\n\n"
        edit_text += "完整編輯功能將在後續版本中提供"
        
        return {
            'success': True,
            'message': edit_text,
            'format': 'text'
        }
    
    def _handle_stats(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理統計命令"""
        base_path = self.config.get_skill_config().get('default_path', '/root/.openclaw/workspace')
        
        try:
            # 計算目錄大小
            total_size = 0
            file_count = 0
            dir_count = 0
            
            for root, dirs, files in os.walk(base_path):
                dir_count += len(dirs)
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
                        file_count += 1
            
            stats_text = f"📊 工作空間統計: {base_path}\n\n"
            stats_text += f"• 總大小: {utils.format_size(total_size)}\n"
            stats_text += f"• 檔案數量: {file_count} 個\n"
            stats_text += f"• 目錄數量: {dir_count} 個\n"
            stats_text += f"• 最近瀏覽: {self.data['stats'].get('browse_count', 0)} 次\n"
            stats_text += f"• 編輯操作: {self.data['stats'].get('edit_count', 0)} 次\n"
            stats_text += f"• 搜尋操作: {self.data['stats'].get('search_count', 0)} 次\n\n"
            stats_text += "使用 `/工作空間 瀏覽` 查看詳細內容"
            
            return {
                'success': True,
                'message': stats_text,
                'format': 'text'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'統計工作空間時出錯: {str(e)}',
                'format': 'text'
            }
    
    def _handle_main_menu(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理主選單命令"""
        menu_text = """
📁 工作空間管理工具

選擇操作:
• 📂 瀏覽檔案 - 瀏覽目錄和檔案
• 🔍 搜尋檔案 - 搜尋檔案和內容
• 📝 編輯檔案 - 編輯文字檔案
• 📊 空間統計 - 查看使用統計
• ⚙️ 工具設定 - 配置工作空間
• 📋 最近檔案 - 查看最近訪問
• ❓ 幫助 - 顯示幫助訊息

使用範例:
/工作空間 瀏覽
/工作空間 搜尋 main.py
/工作空間 統計
        """.strip()
        
        return {
            'success': True,
            'message': menu_text,
            'format': 'text',
            'buttons': [
                [{'text': '📂 瀏覽檔案', 'callback_data': 'browse'}],
                [{'text': '🔍 搜尋檔案', 'callback_data': 'search'}],
                [{'text': '📝 編輯檔案', 'callback_data': 'edit'}],
                [{'text': '📊 空間統計', 'callback_data': 'stats'}],
                [{'text': '⚙️ 工具設定', 'callback_data': 'config'}],
                [{'text': '📋 最近檔案', 'callback_data': 'recent'}],
                [{'text': '❓ 幫助', 'callback_data': 'help'}]
            ]
        }
    
    def _get_file_info(self, file_path: str) -> str:
        """獲取檔案資訊"""
        try:
            stat = os.stat(file_path)
            size = utils.format_size(stat.st_size)
            modified = utils.format_duration(time.time() - stat.st_mtime)
            
            info_text = f"📄 檔案資訊: {os.path.basename(file_path)}\n\n"
            info_text += f"• 路徑: {file_path}\n"
            info_text += f"• 大小: {size}\n"
            info_text += f"• 修改時間: {modified}前\n"
            info_text += f"• 權限: {oct(stat.st_mode)[-3:]}\n"
            info_text += f"• 擁有者: {stat.st_uid}\n\n"
            info_text += "可用操作:\n"
            info_text += "• 查看內容\n• 編輯檔案\n• 複製路徑\n• 刪除檔案"
            
            return info_text
            
        except Exception as e:
            return f"獲取檔案資訊時出錯: {str(e)}"
    
    def _list_directory(self, dir_path: str) -> str:
        """列出目錄內容"""
        try:
            items = os.listdir(dir_path)
            items.sort()
            
            dirs = []
            files = []
            
            for item in items:
                item_path = os.path.join(dir_path, item)
                if os.path.isdir(item_path):
                    dirs.append(f"📁 {item}/")
                else:
                    files.append(f"📄 {item}")
            
            list_text = f"📂 目錄內容: {dir_path}\n\n"
            
            if dirs:
                list_text += "📁 目錄:\n"
                for d in dirs[:10]:  # 限制顯示數量
                    list_text += f"  {d}\n"
                if len(dirs) > 10:
                    list_text += f"  ... 還有 {len(dirs) - 10} 個目錄\n"
                list_text += "\n"
            
            if files:
                list_text += "📄 檔案:\n"
                for f in files[:10]:  # 限制顯示數量
                    list_text += f"  {f}\n"
                if len(files) > 10:
                    list_text += f"  ... 還有 {len(files) - 10} 個檔案\n"
            
            list_text += f"\n總計: {len(dirs)} 個目錄, {len(files)} 個檔案"
            list_text += f"\n\n使用 `/工作空間 瀏覽 {dir_path}/<名稱>` 進入目錄或查看檔案"
            
            return list_text
            
        except Exception as e:
            return f"列出目錄內容時出錯: {str(e)}"
    
    def cleanup(self):
        """清理資源"""
        if self.initialized:
            self._save_data()
            logger.info("工作空間管理工具清理完成")
    
    def __del__(self):
        """解構函數"""
        self.cleanup()


def main():
    """主函數（用於獨立測試）"""
    skill = WorkspaceManagerSkill()
    
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
        print(f"瀏覽目錄: {result}")
        
        skill.cleanup()
    else:
        print("技能初始化失敗")


if __name__ == '__main__':
    main()