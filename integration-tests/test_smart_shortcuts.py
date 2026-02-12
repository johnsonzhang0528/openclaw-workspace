#!/usr/bin/env python3
"""
智慧快捷指令系統整合測試
"""

import asyncio
import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smart_shortcuts.main import SmartShortcuts
from smart_shortcuts.shortcut_manager import ShortcutManager
from smart_shortcuts.template_engine import TemplateEngine
from smart_shortcuts.config import Config

class TestSmartShortcuts(unittest.TestCase):
    """智慧快捷指令測試類別"""
    
    def setUp(self):
        """測試設置"""
        # 創建臨時目錄
        self.temp_dir = tempfile.mkdtemp()
        
        # 創建配置檔案
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        
        config_data = {
            "shortcuts_file": os.path.join(self.temp_dir, 'shortcuts.json'),
            "templates_dir": os.path.join(self.temp_dir, 'templates'),
            "stats_file": os.path.join(self.temp_dir, 'stats.json'),
            "log_level": "INFO",
            "max_shortcuts": 100,
            "max_templates": 50
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
            
    def tearDown(self):
        """測試清理"""
        shutil.rmtree(self.temp_dir)
        
    def test_config_loading(self):
        """測試配置載入"""
        config = Config(self.config_file)
        
        self.assertEqual(config.shortcuts_file, os.path.join(self.temp_dir, 'shortcuts.json'))
        self.assertEqual(config.templates_dir, os.path.join(self.temp_dir, 'templates'))
        self.assertEqual(config.log_level, "INFO")
        
    async def test_shortcut_manager_basic(self):
        """測試快捷指令管理器基本功能"""
        config = Config(self.config_file)
        manager = ShortcutManager(config)
        
        # 載入快捷指令（會創建預設）
        await manager.load_shortcuts()
        
        # 測試快捷指令數量
        self.assertGreater(len(manager.shortcuts), 0)
        
        # 測試獲取快捷指令
        shortcut = manager.get_shortcut("system_info")
        self.assertIsNotNone(shortcut)
        self.assertEqual(shortcut["name"], "系統資訊")
        
        # 測試列出快捷指令
        shortcuts_list = manager.list_shortcuts()
        self.assertGreater(len(shortcuts_list), 0)
        
        # 測試按分類列出
        system_shortcuts = manager.list_shortcuts("system")
        self.assertGreater(len(system_shortcuts), 0)
        
    async def test_shortcut_crud_operations(self):
        """測試快捷指令 CRUD 操作"""
        config = Config(self.config_file)
        manager = ShortcutManager(config)
        
        await manager.load_shortcuts()
        
        # 測試創建快捷指令
        new_shortcut = {
            "name": "測試快捷指令",
            "description": "這是一個測試快捷指令",
            "category": "test",
            "action_type": "command",
            "command": "echo 'Hello, World!'",
            "tags": ["test", "demo"]
        }
        
        result = await manager.create_shortcut(new_shortcut)
        self.assertTrue(result["success"])
        self.assertEqual(result["shortcut"], "測試快捷指令")
        
        # 驗證已添加
        self.assertIn("測試快捷指令", manager.shortcuts)
        
        # 測試更新快捷指令
        update_data = {
            "description": "更新後的描述",
            "command": "echo 'Updated!'"
        }
        
        update_result = await manager.update_shortcut("測試快捷指令", update_data)
        self.assertTrue(update_result["success"])
        self.assertEqual(manager.shortcuts["測試快捷指令"]["description"], "更新後的描述")
        
        # 測試刪除快捷指令
        delete_result = await manager.delete_shortcut("測試快捷指令")
        self.assertTrue(delete_result["success"])
        self.assertNotIn("測試快捷指令", manager.shortcuts)
        
    async def test_shortcut_usage_stats(self):
        """測試快捷指令使用統計"""
        config = Config(self.config_file)
        manager = ShortcutManager(config)
        
        await manager.load_shortcuts()
        
        # 記錄使用
        manager.record_usage("system_info", 0.5)
        manager.record_usage("system_info", 0.3)
        manager.record_usage("list_files", 0.2)
        
        # 獲取統計
        stats = manager.get_stats()
        
        self.assertEqual(stats["total_usage"], 3)
        self.assertEqual(stats["most_used"]["name"], "system_info")
        self.assertEqual(stats["most_used"]["count"], 2)
        
        # 測試最近使用
        recently_used = manager.get_recently_used(limit=5)
        self.assertGreater(len(recently_used), 0)
        
    async def test_shortcut_search(self):
        """測試快捷指令搜尋"""
        config = Config(self.config_file)
        manager = ShortcutManager(config)
        
        await manager.load_shortcuts()
        
        # 搜尋測試
        results = manager.search_shortcuts("系統")
        self.assertGreater(len(results), 0)
        
        # 搜尋標籤
        results = manager.search_shortcuts("diagnostic")
        self.assertGreater(len(results), 0)
        
    async def test_template_engine_basic(self):
        """測試模板引擎基本功能"""
        config = Config(self.config_file)
        engine = TemplateEngine(config)
        
        # 載入模板
        await engine.load_templates()
        
        # 測試模板數量
        self.assertGreater(len(engine.templates), 0)
        
        # 測試獲取模板
        template = engine.get_template("system_info")
        self.assertIsNotNone(template)
        self.assertEqual(template["name"], "系統資訊")
        
        # 測試列出模板
        templates_list = engine.list_templates()
        self.assertGreater(len(templates_list), 0)
        
    async def test_template_rendering(self):
        """測試模板渲染"""
        config = Config(self.config_file)
        engine = TemplateEngine(config)
        
        await engine.load_templates()
        
        # 測試直接渲染
        template_content = "Hello, {{ name }}!"
        context = {"name": "World"}
        
        result = engine.render_template(template_content, context)
        self.assertEqual(result, "Hello, World!")
        
        # 測試通過名稱渲染
        context = {
            "system_info": {
                "node": "test-host",
                "system": "Linux",
                "release": "5.4.0",
                "cpu_count": 4,
                "cpu_percent": 25.5,
                "memory_percent": 65.2,
                "disk_percent": 45.3,
                "boot_time": 1609459200
            }
        }
        
        result = await engine.render_template_by_name("system_info", context)
        self.assertIn("test-host", result)
        self.assertIn("Linux", result)
        self.assertIn("25.5", result)
        
    async def test_template_crud_operations(self):
        """測試模板 CRUD 操作"""
        config = Config(self.config_file)
        engine = TemplateEngine(config)
        
        await engine.load_templates()
        
        # 測試創建模板
        new_template = {
            "name": "測試模板",
            "content": "測試內容: {{ value }}",
            "description": "這是一個測試模板",
            "category": "test",
            "tags": ["test", "demo"]
        }
        
        result = await engine.create_template(new_template)
        self.assertTrue(result["success"])
        self.assertEqual(result["template"], "測試模板")
        
        # 驗證已添加
        self.assertIn("測試模板", engine.templates)
        
        # 測試更新模板
        update_data = {
            "description": "更新後的描述",
            "content": "更新內容: {{ value }}"
        }
        
        update_result = await engine.update_template("測試模板", update_data)
        self.assertTrue(update_result["success"])
        self.assertEqual(engine.templates["測試模板"]["description"], "更新後的描述")
        
        # 測試刪除模板
        delete_result = await engine.delete_template("測試模板")
        self.assertTrue(delete_result["success"])
        self.assertNotIn("測試模板", engine.templates)
        
    def test_template_variable_extraction(self):
        """測試模板變數提取"""
        config = Config(self.config_file)
        engine = TemplateEngine(config)
        
        # 測試變數提取
        template_content = """
        Hello, {{ name }}!
        Today is {{ date }}.
        Values: {{ value1 }}, {{ value2 }}.
        """
        
        variables = engine.extract_variables(template_content)
        
        self.assertEqual(len(variables), 4)
        self.assertIn("name", variables)
        self.assertIn("date", variables)
        self.assertIn("value1", variables)
        self.assertIn("value2", variables)
        
    def test_template_syntax_validation(self):
        """測試模板語法驗證"""
        config = Config(self.config_file)
        engine = TemplateEngine(config)
        
        # 測試有效模板
        valid_template = "Hello, {{ name }}!"
        result = engine.validate_template_syntax(valid_template)
        self.assertTrue(result["valid"])
        
        # 測試無效模板
        invalid_template = "Hello, {{ name }!"
        result = engine.validate_template_syntax(invalid_template)
        self.assertFalse(result["valid"])
        self.assertIn("錯誤", result["message"])
        
    async def test_smart_shortcuts_integration(self):
        """測試智慧快捷指令整合"""
        config = Config(self.config_file)
        shortcuts_system = SmartShortcuts(config)
        
        # 啟動系統
        await shortcuts_system.start()
        
        # 測試系統狀態
        status = shortcuts_system.get_status()
        self.assertTrue(status["running"])
        self.assertGreater(status["shortcuts_count"], 0)
        self.assertGreater(status["templates_count"], 0)
        
        # 測試執行快捷指令
        result = await shortcuts_system.execute_shortcut("system_info")
        self.assertTrue(result["success"])
        self.assertIn("result", result)
        
        # 測試列出快捷指令
        shortcuts_list = await shortcuts_system.list_shortcuts()
        self.assertGreater(len(shortcuts_list), 0)
        
        # 停止系統
        await shortcuts_system.stop()
        
        # 驗證已停止
        status = shortcuts_system.get_status()
        self.assertFalse(status["running"])
        
    @patch('asyncio.create_subprocess_shell')
    async def test_command_execution(self, mock_subprocess):
        """測試命令執行"""
        # 模擬子進程
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Hello, World!", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        config = Config(self.config_file)
        shortcuts_system = SmartShortcuts(config)
        
        await shortcuts_system.start()
        
        # 創建測試快捷指令
        test_shortcut = {
            "name": "test_command",
            "description": "測試命令",
            "category": "test",
            "action_type": "command",
            "command": "echo 'Hello, World!'"
        }
        
        await shortcuts_system.create_shortcut(test_shortcut)
        
        # 執行快捷指令
        result = await shortcuts_system.execute_shortcut("test_command")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["stdout"], "Hello, World!")
        self.assertEqual(result["result"]["returncode"], 0)
        
        await shortcuts_system.stop()
        
    async def test_template_based_shortcut(self):
        """測試基於模板的快捷指令"""
        config = Config(self.config_file)
        shortcuts_system = SmartShortcuts(config)
        
        await shortcuts_system.start()
        
        # 創建模板
        test_template = {
            "name": "greeting",
            "content": "Hello, {{ user }}! Welcome to {{ app }}.",
            "description": "問候模板",
            "category": "test"
        }
        
        await shortcuts_system.template_engine.create_template(test_template)
        
        # 創建基於模板的快捷指令
        template_shortcut = {
            "name": "greet_user",
            "description": "問候用戶",
            "category": "test",
            "action_type": "template",
            "template": "greeting",
            "context": {
                "user": "John",
                "app": "TestApp"
            }
        }
        
        await shortcuts_system.create_shortcut(template_shortcut)
        
        # 執行快捷指令
        result = await shortcuts_system.execute_shortcut("greet_user")
        
        self.assertTrue(result["success"])
        self.assertIn("Hello, John!", result["result"]["result"])
        self.assertIn("Welcome to TestApp", result["result"]["result"])
        
        await shortcuts_system.stop()
        
    async def test_shortcut_import_export(self):
        """測試快捷指令導入導出"""
        config = Config(self.config_file)
        manager = ShortcutManager(config)
        
        await manager.load_shortcuts()
        
        # 導出快捷指令
        export_data = manager.export_shortcuts()
        export_json = json.loads(export_data)
        
        self.assertIn("shortcuts", export_json)
        self.assertIn("count", export_json)
        self.assertEqual(export_json["count"], len(manager.shortcuts))
        
        # 導入快捷指令（合併模式）
        import_result = await manager.import_shortcuts(export_data, merge=True)
        
        self.assertTrue(import_result["success"])
        self.assertEqual(import_result["imported"], 0)  # 應該沒有新導入
        self.assertEqual(import_result["updated"], 0)   # 應該沒有更新
        
        # 測試導入新數據
        new_shortcut_data = {
            "shortcuts": {
                "new_shortcut": {
                    "name": "新快捷指令",
                    "description": "新導入的快捷指令",
                    "category": "import",
                    "action_type": "command",
                    "command": "echo 'Imported'"
                }
            }
        }
        
        new_export_data = json.dumps(new_shortcut_data)
        import_result = await manager.import_shortcuts(new_export_data, merge=True)
        
        self.assertTrue(import_result["success"])
        self.assertEqual(import_result["imported"], 1)
        self.assertIn("新快捷指令", manager.shortcuts)

class TestErrorHandling(unittest.TestCase):
    """錯誤處理測試"""
    
    def setUp(self):
        """測試設置"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """測試清理"""
        shutil.rmtree(self.temp_dir)
        
    async def test_shortcut_not_found(self):
        """測試快捷指令不存在"""
        config = Config(self.config_file)
        shortcuts_system = SmartShortcuts(config)
        
        await shortcuts_system.start()
        
        # 嘗試執行不存在的快捷指令
        result = await shortcuts_system.execute_shortcut("non_existent")
        
        self.assertFalse(result["success"])
        self.assertIn("找不到快捷指令", result["error"])
        
        await shortcuts_system.stop()
        
    async def test_invalid_shortcut_data(self):
        """測試無效的快捷指令數據"""
        config = Config(self.config_file)
        manager = ShortcutManager(config)
        
        await manager.load_shortcuts()
        
        # 測試無效數據
        invalid_shortcut = {
            # 缺少必要字段
        }
        
        result = await manager.create_shortcut(invalid_shortcut)
        
        self.assertFalse(result["success"])
        self.assertIn("錯誤", result["error"])
        
    async def test_template_rendering_error(self):
        """測試模板渲染錯誤"""
        config = Config(self.config_file)
        engine = TemplateEngine(config)
        
        await engine.load_templates()
        
        # 測試缺少變數的模板
        template_content = "Hello, {{ undefined_variable }}!"
        
        with self.assertRaises(Exception):
            engine.render_template(template_content, {})
            
    async def test_command_execution_error(self):
        """測試命令執行錯誤"""
        config = Config(self.config_file)
        shortcuts_system = SmartShortcuts(config)
        
        await shortcuts_system.start()
        
        # 創建會失敗的命令
        failing_shortcut = {
            "name": "failing_command",
            "description": "會失敗的命令",
            "category": "test",
            "action_type": "command",
            "command": "invalid_command_that_does_not_exist"
        }
        
        await shortcuts_system.create_shortcut(failing_shortcut)
        
        # 執行快捷指令
        result = await shortcuts_system.execute_shortcut("failing_command")
        
        # 命令應該失敗
        self.assertTrue(result["success"])  # 執行本身成功
        self.assertFalse(result["result"]["success"])  # 命令執行失敗
        
        await shortcuts_system.stop()

if __name__ == '__main__':
    # 運行測試
    unittest.main()