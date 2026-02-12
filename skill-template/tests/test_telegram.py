#!/usr/bin/env python3
"""
Telegram UI 測試
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加技能目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram_ui import TelegramUI
from config import SkillConfig


class TestTelegramUI(unittest.TestCase):
    """TelegramUI 測試類別"""
    
    def setUp(self):
        """測試設置"""
        # 創建臨時配置檔案
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        
        config_data = {
            "skills": {
                "{{skill_name}}": {
                    "enabled": True,
                    "config": {
                        "telegram_enabled": True,
                        "data_path": os.path.join(self.temp_dir, 'data')
                    }
                }
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)
        
        # 創建配置實例
        self.config = SkillConfig(self.config_file)
        
        # 創建 Telegram UI 實例
        self.ui = TelegramUI(self.config)
    
    def tearDown(self):
        """測試清理"""
        # 清理臨時檔案
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """測試初始化"""
        self.assertFalse(self.ui.initialized)
        
        result = self.ui.initialize()
        self.assertTrue(result)
        self.assertTrue(self.ui.initialized)
    
    def test_create_text_response(self):
        """測試創建文字回應"""
        result = {
            'success': True,
            'message': '測試訊息',
            'format': 'text'
        }
        
        response = self.ui.create_response(result)
        
        self.assertEqual(response['type'], 'text')
        self.assertIn('測試訊息', response['content'])
        self.assertEqual(response['parse_mode'], 'HTML')
    
    def test_create_markdown_response(self):
        """測試創建 Markdown 回應"""
        result = {
            'success': True,
            'message': '測試訊息',
            'format': 'markdown'
        }
        
        response = self.ui.create_response(result)
        
        self.assertEqual(response['type'], 'text')
        self.assertIn('測試訊息', response['content'])
        self.assertEqual(response['parse_mode'], 'Markdown')
    
    def test_create_html_response(self):
        """測試創建 HTML 回應"""
        result = {
            'success': True,
            'message': '測試訊息',
            'format': 'html'
        }
        
        response = self.ui.create_response(result)
        
        self.assertEqual(response['type'], 'text')
        self.assertIn('測試訊息', response['content'])
        self.assertEqual(response['parse_mode'], 'HTML')
    
    def test_create_keyboard_response(self):
        """測試創建鍵盤回應"""
        result = {
            'success': True,
            'message': '測試訊息',
            'format': 'keyboard',
            'buttons': [
                [{'text': '按鈕1', 'callback_data': 'btn1'}],
                [{'text': '按鈕2', 'callback_data': 'btn2'}]
            ]
        }
        
        response = self.ui.create_response(result)
        
        self.assertEqual(response['type'], 'keyboard')
        self.assertIn('測試訊息', response['content'])
        self.assertIn('keyboard', response)
        self.assertIn('inline_keyboard', response['keyboard'])
    
    def test_create_error_response(self):
        """測試創建錯誤回應"""
        result = {
            'success': False,
            'message': '測試錯誤',
            'error': 'TEST_ERROR'
        }
        
        response = self.ui.create_response(result)
        
        self.assertEqual(response['type'], 'keyboard')
        self.assertIn('測試錯誤', response['content'])
        self.assertIn('keyboard', response)
        self.assertIn('inline_keyboard', response['keyboard'])
    
    def test_create_menu(self):
        """測試創建選單"""
        # 測試主選單
        main_menu = self.ui.create_menu('main')
        self.assertIn('message', main_menu)
        self.assertIn('buttons', main_menu)
        self.assertIn('主選單', main_menu['message'])
        
        # 測試配置選單
        config_menu = self.ui.create_menu('config')
        self.assertIn('配置選單', config_menu['message'])
        
        # 測試幫助選單
        help_menu = self.ui.create_menu('help')
        self.assertIn('幫助選單', help_menu['message'])
        
        # 測試未知選單類型（應返回主選單）
        default_menu = self.ui.create_menu('unknown')
        self.assertEqual(default_menu['message'], main_menu['message'])
    
    def test_format_table(self):
        """測試格式化表格"""
        data = [
            {'name': '項目1', 'value': 100, 'status': '正常'},
            {'name': '項目2', 'value': 200, 'status': '警告'},
            {'name': '項目3', 'value': 300, 'status': '錯誤'}
        ]
        
        headers = ['name', 'value', 'status']
        table = self.ui.format_table(data, headers)
        
        self.assertIn('項目1', table)
        self.assertIn('項目2', table)
        self.assertIn('項目3', table)
        self.assertIn('name', table)
        self.assertIn('value', table)
        self.assertIn('status', table)
    
    def test_format_table_auto_headers(self):
        """測試自動生成表頭"""
        data = [
            {'name': '項目1', 'value': 100},
            {'name': '項目2', 'value': 200}
        ]
        
        table = self.ui.format_table(data)
        
        self.assertIn('項目1', table)
        self.assertIn('項目2', table)
        self.assertIn('name', table)
        self.assertIn('value', table)
    
    def test_format_table_empty(self):
        """測試空表格"""
        table = self.ui.format_table([])
        self.assertEqual(table, '無數據')
    
    def test_format_list(self):
        """測試格式化列表"""
        items = ['項目1', '項目2', '項目3']
        formatted = self.ui.format_list(items)
        
        self.assertIn('• 項目1', formatted)
        self.assertIn('• 項目2', formatted)
        self.assertIn('• 項目3', formatted)
    
    def test_format_list_empty(self):
        """測試空列表"""
        formatted = self.ui.format_list([])
        self.assertEqual(formatted, '無項目')
    
    def test_format_list_custom_bullet(self):
        """測試自定義項目符號"""
        items = ['項目1', '項目2']
        formatted = self.ui.format_list(items, '→')
        
        self.assertIn('→ 項目1', formatted)
        self.assertIn('→ 項目2', formatted)
    
    def test_format_code(self):
        """測試格式化程式碼"""
        code = 'print("Hello, World!")'
        
        # 不指定語言
        formatted = self.ui.format_code(code)
        self.assertIn('```\nprint("Hello, World!")\n```', formatted)
        
        # 指定語言
        formatted = self.ui.format_code(code, 'python')
        self.assertIn('```python\nprint("Hello, World!")\n```', formatted)
    
    def test_handle_callback_query(self):
        """測試處理回調查詢"""
        context = {
            'user_id': 'test_user',
            'chat_id': 'test_chat',
            'message_id': 'test_message'
        }
        
        # 測試幫助回調
        result = self.ui.handle_callback_query('help', context)
        self.assertTrue(result['success'])
        self.assertEqual(result['format'], 'keyboard')
        
        # 測試狀態回調
        result = self.ui.handle_callback_query('status', context)
        self.assertTrue(result['success'])
        self.assertEqual(result['format'], 'text')
        
        # 測試配置回調
        result = self.ui.handle_callback_query('config', context)
        self.assertTrue(result['success'])
        self.assertEqual(result['format'], 'keyboard')
        
        # 測試刷新回調
        result = self.ui.handle_callback_query('refresh', context)
        self.assertTrue(result['success'])
        self.assertEqual(result['format'], 'text')
    
    def test_handle_config_action_callback(self):
        """測試處理配置動作回調"""
        context = {
            'user_id': 'test_user',
            'chat_id': 'test_chat',
            'message_id': 'test_message'
        }
        
        # 測試啟用技能
        with patch.object(self.config, 'update_config', return_value=True):
            result = self.ui.handle_callback_query('config_enable', context)
            self.assertTrue(result['success'])
            self.assertIn('✅ 技能已啟用', result['message'])
        
        # 測試停用技能
        with patch.object(self.config, 'update_config', return_value=True):
            result = self.ui.handle_callback_query('config_disable', context)
            self.assertTrue(result['success'])
            self.assertIn('❌ 技能已停用', result['message'])
        
        # 測試切換 Telegram
        with patch.object(self.config, 'update_config', return_value=True):
            result = self.ui.handle_callback_query('config_toggle_telegram', context)
            self.assertTrue(result['success'])
            self.assertIn('🔄 Telegram 狀態已切換', result['message'])
    
    def test_handle_help_action_callback(self):
        """測試處理幫助動作回調"""
        context = {
            'user_id': 'test_user',
            'chat_id': 'test_chat',
            'message_id': 'test_message'
        }
        
        # 測試使用說明
        result = self.ui.handle_callback_query('help_usage', context)
        self.assertTrue(result['success'])
        self.assertIn('使用說明', result['message'])
        
        # 測試故障排除
        result = self.ui.handle_callback_query('help_troubleshoot', context)
        self.assertTrue(result['success'])
        self.assertIn('故障排除', result['message'])
        
        # 測試聯絡支援
        result = self.ui.handle_callback_query('help_contact', context)
        self.assertTrue(result['success'])
        self.assertIn('聯絡支援', result['message'])
    
    def test_handle_unknown_callback(self):
        """測試處理未知回調"""
        context = {
            'user_id': 'test_user',
            'chat_id': 'test_chat',
            'message_id': 'test_message'
        }
        
        result = self.ui.handle_callback_query('unknown_callback', context)
        
        self.assertFalse(result['success'])
        self.assertIn('未知回調', result['message'])
        self.assertIn('error', result)
    
    @patch('telegram_ui.logger')
    def test_handle_callback_error(self, mock_logger):
        """測試處理回調錯誤"""
        context = {
            'user_id': 'test_user',
            'chat_id': 'test_chat',
            'message_id': 'test_message'
        }
        
        # 模擬處理錯誤
        with patch.object(self.ui, '_handle_help_callback', side_effect=Exception('Test error')):
            result = self.ui.handle_callback_query('help', context)
            
            self.assertFalse(result['success'])
            self.assertIn('出錯', result['message'])
            self.assertIn('error', result)


class TestTelegramUIEdgeCases(unittest.TestCase):
    """Telegram UI 邊界情況測試"""
    
    def test_response_without_format(self):
        """測試沒有指定格式的回應"""
        ui = TelegramUI(Mock())
        
        result = {
            'success': True,
            'message': '測試訊息'
            # 沒有 format 欄位
        }
        
        response = ui.create_response(result)
        
        # 應該使用文字格式
        self.assertEqual(response['type'], 'text')
        self.assertIn('測試訊息', response['content'])
    
    def test_response_without_message(self):
        """測試沒有訊息內容的回應"""
        ui = TelegramUI(Mock())
        
        result = {
            'success': True,
            'format': 'text'
            # 沒有 message 欄位
        }
        
        response = ui.create_response(result)
        
        # 應該有空訊息
        self.assertEqual(response['type'], 'text')
        self.assertIsInstance(response['content'], str)
    
    def test_keyboard_response_without_buttons(self):
        """測試鍵盤回應沒有按鈕"""
        ui = TelegramUI(Mock())
        
        result = {
            'success': True,
            'message': '測試訊息',
            'format': 'keyboard'
            # 沒有 buttons 欄位
        }
        
        response = ui.create_response(result)
        
        # 應該有預設按鈕
        self.assertEqual(response['type'], 'keyboard')
        self.assertIn('keyboard', response)
        self.assertIn('inline_keyboard', response['keyboard'])
        self.assertGreater(len(response['keyboard']['inline_keyboard']), 0)


if __name__ == '__main__':
    unittest.main()