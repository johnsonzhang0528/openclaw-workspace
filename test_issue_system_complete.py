#!/usr/bin/env python3
"""
議題系統完整功能測試
測試所有 Telegram 互動介面功能
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加工作空間路徑
workspace_path = '/root/.openclaw/workspace'
sys.path.insert(0, workspace_path)

def test_telegram_integration():
    """測試 Telegram 整合"""
    print("=== 測試 Telegram 整合 ===\n")
    
    try:
        from issue_telegram_integration import get_telegram_integration
        integration = get_telegram_integration()
        
        test_cases = [
            ("/issue", "議題列表命令"),
            ("/issueHistory", "議題歷史命令"),
            ("我們來討論新的主題：AI 輔助決策", "新議題偵測"),
            ("關於資料庫效能優化", "議題相關訊息"),
            ("好的，這個討論差不多了", "結束討論訊息"),
        ]
        
        for command, description in test_cases:
            print(f"測試: {description}")
            print(f"輸入: {command}")
            
            if command.startswith("/"):
                result = integration.handle_telegram_command(command)
            else:
                result = integration.process_message_for_telegram(command)
            
            print(f"成功: {'✅' if result.get('text') or not result.get('text') and 'no_reply' in str(result) else '❌'}")
            print(f"回覆長度: {len(result.get('text', ''))}")
            print(f"按鈕數量: {len(result.get('buttons', []))}")
            
            if result.get('text'):
                print(f"預覽: {result['text'][:50]}...")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Telegram 整合測試失敗: {e}")
        return False

def test_skill_functionality():
    """測試技能功能"""
    print("=== 測試技能功能 ===\n")
    
    try:
        # 添加技能目錄到路徑
        skill_dir = os.path.join(workspace_path, "issue-system-skill")
        sys.path.insert(0, skill_dir)
        
        from main import get_skill
        skill = get_skill()
        
        if not skill.initialize():
            print("❌ 技能初始化失敗")
            return False
        
        print("✅ 技能初始化成功")
        
        # 測試技能資訊
        info = skill.get_skill_info()
        print(f"技能名稱: {info['name']}")
        print(f"版本: {info['version']}")
        print(f"命令數量: {len(info['commands'])}")
        print(f"功能數量: {len(info['capabilities'])}")
        print()
        
        # 測試系統狀態
        status = skill.get_system_status()
        print("系統狀態:")
        print(f"  成功: {status['success']}")
        if status['success']:
            data = status['data']
            print(f"  議題總數: {data.get('total_issues', 0)}")
            print(f"  開啟議題: {data.get('open_issues', 0)}")
            print(f"  關閉議題: {data.get('closed_issues', 0)}")
            print(f"  當前議題: {data.get('current_issue', '無')}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 技能功能測試失敗: {e}")
        return False

def test_openclaw_integration():
    """測試 OpenClaw 整合"""
    print("=== 測試 OpenClaw 整合 ===\n")
    
    try:
        # 添加技能目錄到路徑
        skill_dir = os.path.join(workspace_path, "issue-system-skill")
        sys.path.insert(0, skill_dir)
        
        from integrate_with_openclaw import get_integration
        integration = get_integration()
        
        if not integration.initialize():
            print("❌ 整合初始化失敗")
            return False
        
        print("✅ 整合初始化成功")
        
        # 測試註冊
        from issue_system_skill.integrate_with_openclaw import register_with_openclaw
        register_result = register_with_openclaw()
        
        print("註冊結果:")
        print(f"  成功: {register_result['success']}")
        print(f"  訊息: {register_result['message']}")
        
        if register_result['success']:
            print(f"  技能名稱: {register_result['skill_info']['name']}")
            print(f"  命令數量: {len(register_result['commands'])}")
            print(f"  功能數量: {len(register_result['capabilities'])}")
        
        print()
        
        # 測試訊息處理
        test_context = {
            'user_id': 'test_user',
            'chat_id': 'test_chat',
            'message_id': 'test_msg',
            'platform': 'telegram'
        }
        
        test_messages = [
            ('/issue', "議題列表命令"),
            ('/issueHistory', "議題歷史命令"),
            ('測試新議題建立', "一般訊息"),
        ]
        
        for message, description in test_messages:
            print(f"測試訊息處理: {description}")
            result = integration.handle_message(message, test_context)
            print(f"  成功: {result['success']}")
            print(f"  處理方式: {'技能處理' if not result.get('metadata', {}).get('handled_by_other') else '其他技能處理'}")
            print(f"  按鈕數量: {len(result.get('buttons', []))}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ OpenClaw 整合測試失敗: {e}")
        return False

def test_issue_operations():
    """測試議題操作"""
    print("=== 測試議題操作 ===\n")
    
    try:
        from issue_system_main import get_issue_system
        system = get_issue_system()
        
        # 取得當前議題狀態
        status = system.get_system_status()
        open_issues = status.get('open_issues', 0)
        
        print(f"當前開啟議題: {open_issues}")
        
        if open_issues > 0:
            # 取得一個開啟的議題
            open_issues_list = system.manager.get_open_issues()
            if open_issues_list:
                test_issue = open_issues_list[0]
                print(f"測試議題: {test_issue['title']} (ID: {test_issue['id']})")
                
                # 測試查看議題
                from issue_telegram_integration import get_telegram_integration
                integration = get_telegram_integration()
                
                # 測試查看議題
                view_result = integration.handle_telegram_command(f"/issue_view_{test_issue['id']}")
                print(f"查看議題結果:")
                print(f"  成功: {'✅' if view_result.get('text') else '❌'}")
                print(f"  按鈕數量: {len(view_result.get('buttons', []))}")
                print()
                
                # 測試關閉議題（模擬）
                close_result = integration.handle_telegram_command(f"/issue_close_{test_issue['id']}")
                print(f"關閉議題結果:")
                print(f"  成功: {'✅' if close_result.get('text') else '❌'}")
                print(f"  按鈕數量: {len(close_result.get('buttons', []))}")
                print()
        
        # 測試建立新議題
        print("測試建立新議題:")
        test_message = "測試建立新議題：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        from issue_telegram_integration import get_telegram_integration
        integration = get_telegram_integration()
        
        new_issue_result = integration.process_message_for_telegram(test_message)
        print(f"  輸入: {test_message}")
        print(f"  成功: {'✅' if new_issue_result.get('text') else '❌'}")
        print(f"  按鈕數量: {len(new_issue_result.get('buttons', []))}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 議題操作測試失敗: {e}")
        return False

def test_optimization():
    """測試閱讀成本優化"""
    print("=== 測試閱讀成本優化 ===\n")
    
    try:
        from issue_telegram_integration import get_telegram_integration
        integration = get_telegram_integration()
        
        test_texts = [
            "📋 當前議題列表\n\n目前沒有開啟的議題。",
            "📚 議題歷史記錄\n\n目前沒有已關閉的議題。",
            "📝 網站SEO優化策略\n\n🟢 狀態: 開啟\n📅 建立時間: 2026/02/11 10:30:00\n🔄 最後更新: 2026/02/11 11:45:00\n\n📌 最後討論重點提要:\n關鍵字分析已完成，需要優化網站速度\n\n💬 討論次數: 5",
            "✅ 議題已關閉\n\n📝 網站SEO優化策略\n\n📋 最終摘要已生成，可透過 /issueHistory 查看完整記錄。",
        ]
        
        print("閱讀成本優化測試:")
        for i, text in enumerate(test_texts, 1):
            optimized = integration.optimize_response_text(text)
            print(f"\n測試 {i}:")
            print(f"原始長度: {len(text)} 字元")
            print(f"優化長度: {len(optimized)} 字元")
            print(f"減少: {len(text) - len(optimized)} 字元 ({((len(text) - len(optimized)) / len(text) * 100):.1f}%)")
            print(f"優化預覽: {optimized[:50]}...")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 優化測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🔧 議題系統完整功能測試")
    print("=" * 60)
    
    test_results = []
    
    # 運行所有測試
    tests = [
        ("Telegram 整合", test_telegram_integration),
        ("技能功能", test_skill_functionality),
        ("OpenClaw 整合", test_openclaw_integration),
        ("議題操作", test_issue_operations),
        ("閱讀成本優化", test_optimization),
    ]
    
    for test_name, test_func in tests:
        print(f"\n▶️  開始測試: {test_name}")
        print("-" * 40)
        
        start_time = time.time()
        try:
            success = test_func()
            elapsed = time.time() - start_time
            
            if success:
                print(f"✅ {test_name} 測試通過 ({elapsed:.2f}秒)")
                test_results.append((test_name, True, elapsed))
            else:
                print(f"❌ {test_name} 測試失敗 ({elapsed:.2f}秒)")
                test_results.append((test_name, False, elapsed))
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ {test_name} 測試異常: {e} ({elapsed:.2f}秒)")
            test_results.append((test_name, False, elapsed))
    
    # 顯示測試總結
    print("\n" + "=" * 60)
    print("📊 測試總結")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, success, _ in test_results if success)
    failed_tests = total_tests - passed_tests
    total_time = sum(elapsed for _, _, elapsed in test_results)
    
    print(f"總測試數: {total_tests}")
    print(f"通過測試: {passed_tests}")
    print(f"失敗測試: {failed_tests}")
    print(f"總用時: {total_time:.2f}秒")
    print(f"平均用時: {total_time/total_tests:.2f}秒/測試")
    print()
    
    # 顯示詳細結果
    print("詳細結果:")
    for test_name, success, elapsed in test_results:
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"  {status} {test_name:20} ({elapsed:.2f}秒)")
    
    print("\n" + "=" * 60)
    
    if failed_tests == 0:
        print("🎉 所有測試通過！議題系統功能完整。")
        return 0
    else:
        print(f"⚠️  有 {failed_tests} 個測試失敗，請檢查相關功能。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)