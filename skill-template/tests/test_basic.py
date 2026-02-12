#!/usr/bin/env python3
"""
基本測試
"""

import os
import sys

# 添加技能目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_skill_structure():
    """測試技能結構"""
    # 檢查必要檔案
    required_files = ['SKILL.md', 'package.json', 'main.py']
    for file in required_files:
        file_path = os.path.join(os.path.dirname(__file__), '..', file)
        assert os.path.exists(file_path), f"缺少檔案: {file}"
    
    print("✅ 技能結構測試通過")
    return True

def test_import():
    """測試導入"""
    try:
        import main
        import config
        import telegram_ui
        import utils
        print("✅ 導入測試通過")
        return True
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        return False

def test_config():
    """測試配置"""
    try:
        from config import SkillConfig
        config = SkillConfig()
        assert hasattr(config, 'skill_name')
        assert hasattr(config, 'version')
        print("✅ 配置測試通過")
        return True
    except Exception as e:
        print(f"❌ 配置測試失敗: {e}")
        return False

if __name__ == '__main__':
    print("🧪 運行技能模板測試...")
    
    tests = [
        test_skill_structure,
        test_import,
        test_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 測試 {test.__name__} 失敗: {e}")
    
    print(f"\n📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！")
        sys.exit(0)
    else:
        print("❌ 有測試失敗")
        sys.exit(1)