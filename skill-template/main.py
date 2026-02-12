#!/usr/bin/env python3
"""
{{skill_name}} - OpenClaw 技能主程式
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


class SkillTemplate:
    """技能模板主類別"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化技能"""
        self.config = SkillConfig(config_path)
        self.telegram_ui = TelegramUI(self.config)
        self.initialized = False
        
        logger.info(f"初始化技能模板 v{self.config.version}")
    
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
            logger.info("技能模板初始化完成")
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
                'stats': {}
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
            # 根據命令類型處理
            if command == 'help':
                return self._handle_help(args, context)
            elif command == 'status':
                return self._handle_status(args, context)
            elif command == 'config':
                return self._handle_config(args, context)
            else:
                return self._handle_custom_command(command, args, context)
                
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
技能模板幫助

可用命令:
• /skill-template help - 顯示此幫助訊息
• /skill-template status - 顯示技能狀態
• /skill-template config - 顯示配置資訊

使用範例:
/skill-template status
        """.strip()
        
        return {
            'success': True,
            'message': help_text,
            'format': 'text'
        }
    
    def _handle_status(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理狀態命令"""
        status = {
            'skill': '{{skill_name}}',
            'version': self.config.version,
            'initialized': self.initialized,
            'telegram_enabled': self.config.telegram_enabled,
            'data_path': self.config.data_path,
            'uptime': utils.get_uptime(),
            'stats': self.data.get('stats', {})
        }
        
        status_text = f"""
技能模板狀態

• 版本: {status['version']}
• 狀態: {'已初始化' if status['initialized'] else '未初始化'}
• Telegram: {'已啟用' if status['telegram_enabled'] else '已停用'}
• 資料路徑: {status['data_path']}
• 運行時間: {status['uptime']}
        """.strip()
        
        return {
            'success': True,
            'message': status_text,
            'data': status,
            'format': 'text'
        }
    
    def _handle_config(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理配置命令"""
        config_info = self.config.get_config_info()
        
        config_text = f"""
技能模板配置

• 啟用狀態: {config_info['enabled']}
• Telegram 介面: {config_info['telegram_enabled']}
• 資料路徑: {config_info['data_path']}
• 技能版本: {config_info['version']}
        """.strip()
        
        return {
            'success': True,
            'message': config_text,
            'data': config_info,
            'format': 'text'
        }
    
    def _handle_custom_command(self, command: str, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理自定義命令（由子類別實現）"""
        # 這是模板方法，實際技能應該覆寫這個方法
        return {
            'success': False,
            'message': f'未知命令: {command}',
            'error': 'UNKNOWN_COMMAND'
        }
    
    def cleanup(self):
        """清理資源"""
        if self.initialized:
            self._save_data()
            logger.info("技能模板清理完成")
    
    def __del__(self):
        """解構函數"""
        self.cleanup()


def main():
    """主函數（用於獨立測試）"""
    skill = SkillTemplate()
    
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
        
        skill.cleanup()
    else:
        print("技能初始化失敗")


if __name__ == '__main__':
    main()