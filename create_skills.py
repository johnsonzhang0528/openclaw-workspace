#!/usr/bin/env python3
"""
快速創建技能主程式
"""

import os
import shutil

# 複製技能模板檔案
template_dir = 'skill-template'
skills = ['workspace-manager', 'performance-monitor', 'smart-shortcuts']

for skill in skills:
    print(f'創建 {skill}...')
    skill_dir = os.path.join(skill)
    
    # 複製模板檔案
    for file in ['config.py', 'telegram_ui.py', 'utils.py']:
        src = os.path.join(template_dir, file)
        dst = os.path.join(skill_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    
    # 創建主程式骨架
    class_name = skill.replace('-', '_').title()
    command_name = skill.replace('-', '')
    
    main_content = f'''#!/usr/bin/env python3
"""
{skill} - 主程式
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


class {class_name}Skill:
    """{skill} 主類別"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化技能"""
        self.config = SkillConfig(config_path)
        self.telegram_ui = TelegramUI(self.config)
        self.initialized = False
        
        logger.info(f'初始化 {skill} v{{self.config.version}}')
    
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
            logger.info(f'{skill} 初始化完成')
            return True
            
        except Exception as e:
            logger.error(f'初始化失敗: {{e}}')
            return False
    
    def _load_data(self):
        """加載技能資料"""
        data_file = os.path.join(self.config.data_path, 'data.json')
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {{
                'version': self.config.version,
                'created_at': utils.get_current_timestamp(),
                'stats': {{}}
            }}
    
    def _save_data(self):
        """儲存技能資料"""
        data_file = os.path.join(self.config.data_path, 'data.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def handle_command(self, command: str, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理命令"""
        if not self.initialized:
            return {{
                'success': False,
                'message': '技能未初始化',
                'error': 'NOT_INITIALIZED'
            }}
        
        try:
            # 根據命令類型處理
            if command == 'help':
                return self._handle_help(args, context)
            elif command == 'status':
                return self._handle_status(args, context)
            elif command == 'config':
                return self._handle_config(args, context)
            else:
                return self._handle_main_menu(args, context)
                
        except Exception as e:
            logger.error(f'處理命令 {{command}} 時出錯: {{e}}')
            return {{
                'success': False,
                'message': f'處理命令時出錯: {{str(e)}}',
                'error': 'COMMAND_ERROR'
            }}
    
    def _handle_help(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理幫助命令"""
        help_text = f'''
{skill} 幫助

可用命令:
- /{command_name} help - 顯示此幫助訊息
- /{command_name} status - 顯示技能狀態
- /{command_name} config - 顯示配置資訊

使用範例:
/{command_name} status
        '''.strip()
        
        return {{
            'success': True,
            'message': help_text,
            'format': 'text'
        }}
    
    def _handle_status(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理狀態命令"""
        status = {{
            'skill': '{skill}',
            'version': self.config.version,
            'initialized': self.initialized,
            'telegram_enabled': self.config.telegram_enabled,
            'data_path': self.config.data_path,
            'uptime': utils.get_uptime(),
            'stats': self.data.get('stats', {{}})
        }}
        
        status_text = f'''
{skill} 狀態

- 版本: {{status["version"]}}
- 狀態: {{'已初始化' if status["initialized"] else '未初始化'}}
- Telegram: {{'已啟用' if status["telegram_enabled"] else '已停用'}}
- 資料路徑: {{status["data_path"]}}
- 運行時間: {{status["uptime"]}}
        '''.strip()
        
        return {{
            'success': True,
            'message': status_text,
            'data': status,
            'format': 'text'
        }}
    
    def _handle_config(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理配置命令"""
        config_info = self.config.get_config_info()
        
        config_text = f'''
{skill} 配置

- 啟用狀態: {{config_info["enabled"]}}
- Telegram 介面: {{config_info["telegram_enabled"]}}
- 資料路徑: {{config_info["data_path"]}}
- 技能版本: {{config_info["version"]}}
        '''.strip()
        
        return {{
            'success': True,
            'message': config_text,
            'data': config_info,
            'format': 'text'
        }}
    
    def _handle_main_menu(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理主選單命令"""
        menu_text = f'''
{skill} 主選單

功能開發中...
        '''.strip()
        
        return {{
            'success': True,
            'message': menu_text,
            'format': 'text'
        }}
    
    def cleanup(self):
        """清理資源"""
        if self.initialized:
            self._save_data()
            logger.info(f'{skill} 清理完成')
    
    def __del__(self):
        """解構函數"""
        self.cleanup()


def main():
    """主函數（用於獨立測試）"""
    skill = {class_name}Skill()
    
    if skill.initialize():
        print('技能初始化成功')
        
        # 測試命令處理
        test_context = {{
            'user_id': 'test_user',
            'chat_id': 'test_chat',
            'platform': 'cli'
        }}
        
        result = skill.handle_command('status', [], test_context)
        print(f'狀態檢查: {{result}}')
        
        skill.cleanup()
    else:
        print('技能初始化失敗')


if __name__ == '__main__':
    main()
'''
    
    with open(os.path.join(skill_dir, 'main.py'), 'w', encoding='utf-8') as f:
        f.write(main_content)
    
    print(f'✅ {skill} 創建完成')

print('所有技能主程式創建完成！')