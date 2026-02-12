#!/usr/bin/env python3
"""
Telegram 介面模組
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramUI:
    """Telegram 使用者介面處理"""
    
    def __init__(self, config):
        """初始化 Telegram UI
        
        Args:
            config: 技能配置
        """
        self.config = config
        self.bot = None
        self.initialized = False
        
    def initialize(self) -> bool:
        """初始化 Telegram 介面
        
        Returns:
            是否成功
        """
        try:
            # 這裡應該初始化 Telegram Bot
            # 實際實現會根據 OpenClaw 的 Telegram 插件來處理
            logger.info("Telegram UI 初始化完成")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Telegram UI 初始化失敗: {e}")
            return False
    
    def create_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """創建 Telegram 回應
        
        Args:
            result: 命令處理結果
            
        Returns:
            Telegram 回應格式
        """
        if not result.get('success', False):
            return self._create_error_response(result)
        
        # 根據格式創建回應
        format_type = result.get('format', 'text')
        
        if format_type == 'text':
            return self._create_text_response(result)
        elif format_type == 'markdown':
            return self._create_markdown_response(result)
        elif format_type == 'html':
            return self._create_html_response(result)
        elif format_type == 'keyboard':
            return self._create_keyboard_response(result)
        else:
            return self._create_text_response(result)
    
    def _create_text_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """創建文字回應"""
        message = result.get('message', '')
        
        # 添加時間戳
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"🕐 {timestamp}\n\n{message}"
        
        return {
            'type': 'text',
            'content': formatted_message,
            'parse_mode': 'HTML'
        }
    
    def _create_markdown_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """創建 Markdown 回應"""
        message = result.get('message', '')
        
        # 添加標題
        formatted_message = f"*{{skill_name}}*\n\n{message}"
        
        return {
            'type': 'text',
            'content': formatted_message,
            'parse_mode': 'Markdown'
        }
    
    def _create_html_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """創建 HTML 回應"""
        message = result.get('message', '')
        
        # 添加 HTML 格式
        formatted_message = f"<b>{{skill_name}}</b>\n\n{message}"
        
        return {
            'type': 'text',
            'content': formatted_message,
            'parse_mode': 'HTML'
        }
    
    def _create_keyboard_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """創建鍵盤回應"""
        message = result.get('message', '')
        buttons = result.get('buttons', [])
        
        # 創建 inline keyboard
        keyboard = self._create_inline_keyboard(buttons)
        
        return {
            'type': 'keyboard',
            'content': message,
            'keyboard': keyboard,
            'parse_mode': 'HTML'
        }
    
    def _create_error_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """創建錯誤回應"""
        error_message = result.get('message', '發生未知錯誤')
        error_code = result.get('error', 'UNKNOWN_ERROR')
        
        formatted_message = f"❌ 錯誤: {error_message}\n\n錯誤代碼: {error_code}"
        
        # 添加幫助按鈕
        buttons = [
            [{'text': '🆘 獲取幫助', 'callback_data': 'help'}],
            [{'text': '🔄 重試', 'callback_data': 'retry'}]
        ]
        
        return {
            'type': 'keyboard',
            'content': formatted_message,
            'keyboard': {
                'inline_keyboard': buttons
            },
            'parse_mode': 'HTML'
        }
    
    def _create_inline_keyboard(self, buttons: List[List[Dict[str, str]]]) -> Dict[str, Any]:
        """創建 inline keyboard
        
        Args:
            buttons: 按鈕列表，每個按鈕是 {'text': '按鈕文字', 'callback_data': '數據'}
            
        Returns:
            keyboard 配置
        """
        if not buttons:
            # 預設按鈕
            buttons = [
                [{'text': 'ℹ️ 幫助', 'callback_data': 'help'}],
                [{'text': '📊 狀態', 'callback_data': 'status'}],
                [{'text': '⚙️ 配置', 'callback_data': 'config'}]
            ]
        
        return {
            'inline_keyboard': buttons
        }
    
    def create_menu(self, menu_type: str = 'main') -> Dict[str, Any]:
        """創建選單
        
        Args:
            menu_type: 選單類型
            
        Returns:
            選單配置
        """
        menus = {
            'main': {
                'message': '{{skill_name}} 主選單',
                'buttons': [
                    [{'text': '📊 狀態', 'callback_data': 'status'}],
                    [{'text': '⚙️ 配置', 'callback_data': 'config'}],
                    [{'text': '📖 幫助', 'callback_data': 'help'}],
                    [{'text': '🔄 刷新', 'callback_data': 'refresh'}]
                ]
            },
            'config': {
                'message': '配置選單',
                'buttons': [
                    [{'text': '✅ 啟用技能', 'callback_data': 'config_enable'}],
                    [{'text': '❌ 停用技能', 'callback_data': 'config_disable'}],
                    [{'text': '📱 Telegram 開關', 'callback_data': 'config_toggle_telegram'}],
                    [{'text': '🔙 返回主選單', 'callback_data': 'main'}]
                ]
            },
            'help': {
                'message': '幫助選單',
                'buttons': [
                    [{'text': '📚 使用說明', 'callback_data': 'help_usage'}],
                    [{'text': '🛠️ 故障排除', 'callback_data': 'help_troubleshoot'}],
                    [{'text': '📞 聯絡支援', 'callback_data': 'help_contact'}],
                    [{'text': '🔙 返回主選單', 'callback_data': 'main'}]
                ]
            }
        }
        
        return menus.get(menu_type, menus['main'])
    
    def format_table(self, data: List[Dict[str, Any]], headers: List[str] = None) -> str:
        """格式化表格數據
        
        Args:
            data: 表格數據
            headers: 表頭
            
        Returns:
            格式化後的表格文字
        """
        if not data:
            return "無數據"
        
        # 自動生成表頭
        if not headers:
            headers = list(data[0].keys())
        
        # 計算每列最大寬度
        col_widths = []
        for header in headers:
            max_width = len(str(header))
            for row in data:
                value = str(row.get(header, ''))
                max_width = max(max_width, len(value))
            col_widths.append(max_width + 2)  # 添加邊距
        
        # 創建分隔線
        separator = '+' + '+'.join(['-' * w for w in col_widths]) + '+'
        
        # 創建表頭
        table_lines = [separator]
        header_line = '|'
        for i, header in enumerate(headers):
            header_line += f" {header:<{col_widths[i]-1}}|"
        table_lines.append(header_line)
        table_lines.append(separator)
        
        # 添加數據行
        for row in data:
            row_line = '|'
            for i, header in enumerate(headers):
                value = str(row.get(header, ''))
                row_line += f" {value:<{col_widths[i]-1}}|"
            table_lines.append(row_line)
        
        table_lines.append(separator)
        
        return '\n'.join(table_lines)
    
    def format_list(self, items: List[str], bullet: str = '•') -> str:
        """格式化列表
        
        Args:
            items: 項目列表
            bullet: 項目符號
            
        Returns:
            格式化後的列表
        """
        if not items:
            return "無項目"
        
        return '\n'.join([f"{bullet} {item}" for item in items])
    
    def format_code(self, code: str, language: str = '') -> str:
        """格式化程式碼
        
        Args:
            code: 程式碼
            language: 程式語言
            
        Returns:
            格式化後的程式碼
        """
        if language:
            return f"```{language}\n{code}\n```"
        else:
            return f"```\n{code}\n```"
    
    def handle_callback_query(self, callback_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理回調查詢
        
        Args:
            callback_data: 回調數據
            context: 上下文
            
        Returns:
            處理結果
        """
        try:
            # 解析回調數據
            if callback_data == 'help':
                return self._handle_help_callback(context)
            elif callback_data == 'status':
                return self._handle_status_callback(context)
            elif callback_data == 'config':
                return self._handle_config_callback(context)
            elif callback_data == 'refresh':
                return self._handle_refresh_callback(context)
            elif callback_data.startswith('config_'):
                return self._handle_config_action_callback(callback_data, context)
            elif callback_data.startswith('help_'):
                return self._handle_help_action_callback(callback_data, context)
            else:
                return {
                    'success': False,
                    'message': f'未知回調: {callback_data}',
                    'error': 'UNKNOWN_CALLBACK'
                }
                
        except Exception as e:
            logger.error(f"處理回調查詢失敗: {e}")
            return {
                'success': False,
                'message': f'處理回調時出錯: {str(e)}',
                'error': 'CALLBACK_ERROR'
            }
    
    def _handle_help_callback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理幫助回調"""
        help_menu = self.create_menu('help')
        
        return {
            'success': True,
            'message': help_menu['message'],
            'buttons': help_menu['buttons'],
            'format': 'keyboard'
        }
    
    def _handle_status_callback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理狀態回調"""
        status_info = {
            'skill': '{{skill_name}}',
            'version': '1.0.0',
            'telegram_enabled': self.config.telegram_enabled,
            'data_path': self.config.data_path,
            'timestamp': datetime.now().isoformat()
        }
        
        status_text = f"""
{{skill_name}} 狀態

• 版本: {status_info['version']}
• Telegram: {'✅ 已啟用' if status_info['telegram_enabled'] else '❌ 已停用'}
• 資料路徑: {status_info['data_path']}
• 檢查時間: {status_info['timestamp']}
        """.strip()
        
        return {
            'success': True,
            'message': status_text,
            'format': 'text'
        }
    
    def _handle_config_callback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理配置回調"""
        config_menu = self.create_menu('config')
        
        return {
            'success': True,
            'message': config_menu['message'],
            'buttons': config_menu['buttons'],
            'format': 'keyboard'
        }
    
    def _handle_refresh_callback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理刷新回調"""
        return {
            'success': True,
            'message': '✅ 已刷新',
            'format': 'text'
        }
    
    def _handle_config_action_callback(self, callback_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理配置動作回調"""
        action = callback_data.replace('config_', '')
        
        actions = {
            'enable': ('✅ 技能已啟用', {'enabled': True}),
            'disable': ('❌ 技能已停用', {'enabled': False}),
            'toggle_telegram': ('🔄 Telegram 狀態已切換', {'config': {'telegram_enabled': not self.config.telegram_enabled}})
        }
        
        if action in actions:
            message, updates = actions[action]
            
            # 更新配置
            if self.config.update_config(updates):
                return {
                    'success': True,
                    'message': message,
                    'format': 'text'
                }
            else:
                return {
                    'success': False,
                    'message': '❌ 更新配置失敗',
                    'error': 'CONFIG_UPDATE_FAILED'
                }
        else:
            return {
                'success': False,
                'message': f'未知配置動作: {action}',
                'error': 'UNKNOWN_CONFIG_ACTION'
            }
    
    def _handle_help_action_callback(self, callback_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理幫助動作回調"""
        action = callback_data.replace('help_', '')
        
        help_texts = {
            'usage': """
{{skill_name}} 使用說明

基本命令:
• /{{command_prefix}} help - 顯示幫助
• /{{command_prefix}} status - 顯示狀態
• /{{command_prefix}} config - 顯示配置

使用範例:
/{{command_prefix}} status
            """,
            'troubleshoot': """
故障排除

常見問題:
1. 技能未回應
   - 檢查技能是否啟用
   - 重啟 OpenClaw: openclaw gateway restart

2. Telegram 介面無效
   - 檢查 Telegram 配置
   - 確認 bot token 正確

3. 配置錯誤
   - 檢查 openclaw.json 格式
   - 驗證配置路徑權限
            """,
            'contact': """
聯絡支援

• 問題回報: {{issues_url}}
• 討論區: {{forum_url}}
• 電子郵件: {{email}}
            """
        }
        
        if action in help_texts:
            return {
                'success': True,
                'message': help_texts[action].strip(),
                'format': 'text'
            }
        else:
            return {
                'success': False,
                'message': f'未知幫助主題: {action}',
                'error': 'UNKNOWN_HELP_TOPIC'
            }


if __name__ == '__main__':
    # 測試 Telegram UI
    from config import SkillConfig
    
    config = SkillConfig()
    ui = TelegramUI(config)
    
    # 測試回應創建
    test_result = {
        'success': True,
        'message': '測試訊息',
        'format': 'text'
    }
    
    response = ui.create_response(test_result)
    print(f"文字回應: {response}")
    
    # 測試表格格式化
    test_data = [
        {'name': '項目1', 'value': 100, 'status': '正常'},
        {'name': '項目2', 'value': 200, 'status': '警告'},
        {'name': '項目3', 'value': 300, 'status': '錯誤'}
    ]
    
    table = ui.format_table(test_data)
    print(f"\n表格:\n{table}")
    
    # 測試選單創建
    menu = ui.create_menu('main')
    print(f"\n主選單: {menu}")