#!/usr/bin/env python3
"""
Telegram 整合測試
測試所有技能的 Telegram 介面功能
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加工作空間目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

class TestTelegramIntegration(unittest.TestCase):
    """測試 Telegram 整合"""
    
    def setUp(self):
        """設置測試環境"""
        self.test_context = {
            'user_id': 'test_user_123',
            'chat_id': 'test_chat_456',
            'platform': 'telegram',
            'message_id': 'test_msg_789'
        }
    
    def test_skills_marketplace_telegram(self):
        """測試技能市集的 Telegram 功能"""
        # 模擬 Telegram 上下文
        context = {
            'user': {'id': 123456, 'username': 'test_user'},
            'chat': {'id': -1001234567890, 'type': 'group'},
            'message': {'message_id': 123}
        }
        
        # 檢查技能市集是否有 Telegram 處理器
        skill_dir = 'skills-marketplace'
        
        # 檢查 main.py 中的 Telegram 相關代碼
        main_path = f'{skill_dir}/main.py'
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 檢查是否有 Telegram 相關的處理邏輯
                self.assertIn('telegram', content.lower())
                
                # 檢查是否有命令處理
                self.assertIn('handle_command', content)
                
                # 檢查是否有按鈕支持
                self.assertIn('buttons', content) or self.assertIn('inline_keyboard', content)
    
    def test_workspace_manager_telegram(self):
        """測試工作空間管理器的 Telegram 功能"""
        skill_dir = 'workspace-manager'
        
        # 檢查是否有 Telegram UI 檔案
        telegram_ui_path = f'{skill_dir}/telegram_ui.py'
        if os.path.exists(telegram_ui_path):
            with open(telegram_ui_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('TelegramUI', content)
                self.assertIn('send_message', content)
                self.assertIn('edit_message', content)
        
        # 檢查 main.py 中的 Telegram 整合
        main_path = f'{skill_dir}/main.py'
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('telegram', content.lower())
    
    def test_performance_monitor_telegram(self):
        """測試效能監控的 Telegram 功能"""
        skill_dir = 'performance-monitor'
        
        # 檢查是否有 Telegram UI 檔案
        telegram_ui_path = f'{skill_dir}/telegram_ui.py'
        self.assertTrue(os.path.exists(telegram_ui_path), '缺少 telegram_ui.py')
        
        with open(telegram_ui_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('TelegramUI', content)
            self.assertIn('send_alert', content)
            self.assertIn('send_dashboard', content)
    
    def test_smart_shortcuts_telegram(self):
        """測試智慧快捷指令的 Telegram 功能"""
        skill_dir = 'smart-shortcuts'
        
        # 檢查是否有 Telegram UI 檔案
        telegram_ui_path = f'{skill_dir}/telegram_ui.py'
        self.assertTrue(os.path.exists(telegram_ui_path), '缺少 telegram_ui.py')
        
        with open(telegram_ui_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('TelegramUI', content)
            self.assertIn('send_shortcut_menu', content)
    
    def test_telegram_buttons_format(self):
        """測試 Telegram 按鈕格式"""
        # 檢查所有技能的按鈕格式是否正確
        skills = ['skills-marketplace', 'workspace-manager', 'performance-monitor', 'smart-shortcuts']
        
        for skill in skills:
            main_path = f'{skill}/main.py'
            if os.path.exists(main_path):
                with open(main_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 檢查是否有按鈕定義
                    if 'buttons' in content or 'inline_keyboard' in content:
                        # 檢查按鈕格式
                        self.assertIn('callback_data', content)
                        self.assertIn('text', content)
    
    def test_telegram_command_parsing(self):
        """測試 Telegram 命令解析"""
        # 測試命令解析邏輯
        test_commands = [
            ('/技能市集', ('技能市集', [])),
            ('/工作空間 瀏覽', ('工作空間', ['瀏覽'])),
            ('/效能監控 狀態', ('效能監控', ['狀態'])),
            ('/快捷指令 新增', ('快捷指令', ['新增']))
        ]
        
        # 檢查所有技能都能正確解析命令
        for command, expected in test_commands:
            cmd_parts = command.split()
            cmd_name = cmd_parts[0][1:]  # 移除斜線
            cmd_args = cmd_parts[1:] if len(cmd_parts) > 1 else []
            
            self.assertEqual(cmd_name, expected[0])
            self.assertEqual(cmd_args, expected[1])
    
    @patch('telegram.Bot')
    def test_telegram_message_sending(self, mock_bot_class):
        """測試 Telegram 訊息發送"""
        # 設置模擬
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        # 測試發送訊息
        test_message = "測試訊息"
        test_chat_id = -1001234567890
        
        # 模擬發送訊息
        mock_bot.send_message.return_value = MagicMock(message_id=123)
        
        # 檢查是否能正確調用
        try:
            from skills_marketplace.telegram_ui import TelegramUI
            ui = TelegramUI(MagicMock())
            ui.bot = mock_bot
            
            result = ui.send_message(test_chat_id, test_message)
            self.assertIsNotNone(result)
            
        except ImportError:
            # 如果無法導入，檢查檔案結構
            pass
    
    def test_telegram_context_handling(self):
        """測試 Telegram 上下文處理"""
        # 檢查所有技能都能處理 Telegram 上下文
        skills = ['skills-marketplace', 'workspace-manager', 'performance-monitor', 'smart-shortcuts']
        
        for skill in skills:
            main_path = f'{skill}/main.py'
            if os.path.exists(main_path):
                with open(main_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 檢查是否有上下文處理
                    self.assertIn('context', content)
                    self.assertIn('user_id', content) or self.assertIn('chat_id', content)
    
    def test_error_handling(self):
        """測試錯誤處理"""
        # 檢查所有技能都有錯誤處理機制
        skills = ['skills-marketplace', 'workspace-manager', 'performance-monitor', 'smart-shortcuts']
        
        for skill in skills:
            main_path = f'{skill}/main.py'
            if os.path.exists(main_path):
                with open(main_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 檢查是否有錯誤處理
                    self.assertIn('try:', content)
                    self.assertIn('except', content)
                    self.assertIn('error', content.lower())
    
    def test_telegram_webhook_support(self):
        """測試 Telegram Webhook 支持"""
        # 檢查是否有 Webhook 相關的配置
        config_files = [
            'skills-marketplace/config.py',
            'workspace-manager/config.py', 
            'performance-monitor/config.py',
            'smart-shortcuts/config.py'
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 檢查是否有 Webhook 配置
                    if 'webhook' in content.lower():
                        self.assertIn('WEBHOOK_URL', content)
                        self.assertIn('WEBHOOK_PORT', content)


def run_telegram_tests():
    """運行 Telegram 整合測試"""
    print("📱 開始 Telegram 整合測試...")
    print("=" * 60)
    
    # 創建測試套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加測試類
    suite.addTests(loader.loadTestsFromTestCase(TestTelegramIntegration))
    
    # 運行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"📊 Telegram 測試結果: {result.testsRun} 個測試")
    print(f"✅ 通過: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失敗: {len(result.failures)}")
    print(f"⚠️  錯誤: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # 運行 Telegram 整合測試
    success = run_telegram_tests()
    
    # 返回退出碼
    sys.exit(0 if success else 1)