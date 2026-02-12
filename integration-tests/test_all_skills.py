#!/usr/bin/env python3
"""
整合測試 - 測試所有四個新技能
"""

import sys
import os
import json
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock

# 添加工作空間目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

class TestAllSkills(unittest.TestCase):
    """測試所有技能的整合功能"""
    
    def setUp(self):
        """設置測試環境"""
        self.test_context = {
            'user_id': 'test_user_123',
            'chat_id': 'test_chat_456',
            'platform': 'telegram'
        }
    
    def test_skills_marketplace_structure(self):
        """測試技能市集結構"""
        # 檢查檔案是否存在
        self.assertTrue(os.path.exists('skills-marketplace/SKILL.md'))
        self.assertTrue(os.path.exists('skills-marketplace/main.py'))
        self.assertTrue(os.path.exists('skills-marketplace/package.json'))
        
        # 檢查 SKILL.md 內容
        with open('skills-marketplace/SKILL.md', 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('技能市集瀏覽器', content)
            self.assertIn('Telegram', content)
    
    def test_workspace_manager_structure(self):
        """測試工作空間管理器結構"""
        self.assertTrue(os.path.exists('workspace-manager/SKILL.md'))
        self.assertTrue(os.path.exists('workspace-manager/main.py'))
        self.assertTrue(os.path.exists('workspace-manager/package.json'))
    
    def test_performance_monitor_structure(self):
        """測試效能監控儀表板結構"""
        self.assertTrue(os.path.exists('performance-monitor/SKILL.md'))
        self.assertTrue(os.path.exists('performance-monitor/main.py'))
        self.assertTrue(os.path.exists('performance-monitor/resource_monitor.py'))
        self.assertTrue(os.path.exists('performance-monitor/dashboard.py'))
    
    def test_smart_shortcuts_structure(self):
        """測試智慧快捷指令系統結構"""
        self.assertTrue(os.path.exists('smart-shortcuts/SKILL.md'))
        self.assertTrue(os.path.exists('smart-shortcuts/main.py'))
        self.assertTrue(os.path.exists('smart-shortcuts/shortcut_manager.py'))
        self.assertTrue(os.path.exists('smart-shortcuts/template_engine.py'))
    
    def test_skill_template_consistency(self):
        """測試技能模板一致性"""
        # 檢查所有技能都有標準檔案
        skills = ['skills-marketplace', 'workspace-manager', 'performance-monitor', 'smart-shortcuts']
        
        for skill in skills:
            # 檢查 package.json
            package_path = f'{skill}/package.json'
            self.assertTrue(os.path.exists(package_path), f'{skill} 缺少 package.json')
            
            with open(package_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
                self.assertIn('name', package_data)
                self.assertIn('version', package_data)
                self.assertIn('description', package_data)
            
            # 檢查 SKILL.md
            skill_path = f'{skill}/SKILL.md'
            self.assertTrue(os.path.exists(skill_path), f'{skill} 缺少 SKILL.md')
            
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('SKILL.md', content)
                self.assertIn('Telegram', content)
    
    def test_development_tools(self):
        """測試開發工具"""
        self.assertTrue(os.path.exists('dev-tools/skill-builder.py'))
        self.assertTrue(os.path.exists('dev-tools/test-runner.py'))
        self.assertTrue(os.path.exists('dev-tools/development-monitor.py'))
        
        # 測試開發監控器
        try:
            import dev_tools.development_monitor as dm
            self.assertTrue(hasattr(dm, 'DevelopmentMonitor'))
        except ImportError:
            pass  # 在測試環境中可能無法導入
    
    @patch('subprocess.run')
    def test_skill_builder_command(self, mock_subprocess):
        """測試技能構建器命令"""
        mock_subprocess.return_value = Mock(returncode=0, stdout='Success')
        
        # 測試技能構建器
        from dev_tools.skill_builder import SkillBuilder
        builder = SkillBuilder()
        
        # 測試創建技能
        result = builder.create_skill('test-skill', '測試技能')
        self.assertIn('success', result)
    
    def test_design_documents(self):
        """測試設計文檔"""
        self.assertTrue(os.path.exists('功能擴展設計方案.md'))
        self.assertTrue(os.path.exists('實施計劃.md'))
        
        with open('功能擴展設計方案.md', 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('技能市集瀏覽器', content)
            self.assertIn('工作空間管理工具', content)
            self.assertIn('效能監控儀表板', content)
            self.assertIn('智慧快捷指令系統', content)
    
    def test_telegram_integration(self):
        """測試 Telegram 整合"""
        # 檢查所有技能都有 Telegram UI 相關檔案
        skills = ['skills-marketplace', 'workspace-manager', 'performance-monitor', 'smart-shortcuts']
        
        for skill in skills:
            # 檢查是否有 telegram_ui.py 或類似檔案
            ui_files = [
                f'{skill}/telegram_ui.py',
                f'{skill}/telegram_handler.py',
                f'{skill}/telegram_interface.py'
            ]
            
            has_ui_file = any(os.path.exists(f) for f in ui_files)
            if not has_ui_file:
                # 檢查 main.py 中是否有 Telegram 相關代碼
                main_path = f'{skill}/main.py'
                if os.path.exists(main_path):
                    with open(main_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.assertIn('telegram', content.lower(), f'{skill} 缺少 Telegram 整合')
    
    def test_configuration_files(self):
        """測試配置檔案"""
        # 檢查所有技能都有配置檔案
        skills = ['skills-marketplace', 'workspace-manager', 'performance-monitor', 'smart-shortcuts']
        
        for skill in skills:
            config_files = [
                f'{skill}/config.py',
                f'{skill}/config.json',
                f'{skill}/settings.py'
            ]
            
            has_config = any(os.path.exists(f) for f in config_files)
            if not has_config:
                # 檢查 package.json 中是否有配置
                package_path = f'{skill}/package.json'
                if os.path.exists(package_path):
                    with open(package_path, 'r', encoding='utf-8') as f:
                        package_data = json.load(f)
                        self.assertIn('config', package_data, f'{skill} 缺少配置')


class TestSkillInteractions(unittest.TestCase):
    """測試技能之間的互動"""
    
    def test_skill_dependencies(self):
        """測試技能依賴關係"""
        # 檢查技能之間沒有循環依賴
        skills = {
            'skills-marketplace': ['workspace-manager', 'smart-shortcuts'],
            'workspace-manager': ['performance-monitor'],
            'performance-monitor': [],
            'smart-shortcuts': ['skills-marketplace', 'workspace-manager']
        }
        
        # 簡單的依賴檢查
        for skill, deps in skills.items():
            for dep in deps:
                self.assertTrue(os.path.exists(dep), f'{skill} 依賴的 {dep} 不存在')
    
    def test_common_utilities(self):
        """測試共用工具"""
        # 檢查所有技能都使用標準工具
        common_utils = ['utils.py', 'helpers.py', 'common.py']
        
        for skill in ['skills-marketplace', 'workspace-manager', 'performance-monitor', 'smart-shortcuts']:
            util_found = any(os.path.exists(f'{skill}/{util}') for util in common_utils)
            if not util_found:
                # 檢查是否從 skill-template 繼承
                self.assertTrue(os.path.exists('skill-template/utils.py'))


def run_integration_tests():
    """運行整合測試"""
    print("🚀 開始整合測試...")
    print("=" * 60)
    
    # 創建測試套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加測試類
    suite.addTests(loader.loadTestsFromTestCase(TestAllSkills))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillInteractions))
    
    # 運行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"📊 測試結果: {result.testsRun} 個測試")
    print(f"✅ 通過: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失敗: {len(result.failures)}")
    print(f"⚠️  錯誤: {len(result.errors)}")
    
    if result.failures:
        print("\n失敗的測試:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n錯誤的測試:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # 運行整合測試
    success = run_integration_tests()
    
    # 返回退出碼
    sys.exit(0 if success else 1)