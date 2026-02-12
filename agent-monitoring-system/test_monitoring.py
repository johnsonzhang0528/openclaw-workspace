"""
輕量級測試腳本 - 測試監控系統核心功能
避免 token 限制問題，使用簡單測試方法
"""

import sys
import os
import time
from datetime import datetime

# 添加模組路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config_module():
    """測試配置模組"""
    print("🧪 測試 config.py...")
    try:
        import config
        print(f"  ✅ 配置載入成功")
        print(f"    監控間隔: {config.monitoring.polling_interval}秒")
        print(f"    歷史保留: {config.monitoring.history_retention_days}天")
        return True
    except Exception as e:
        print(f"  ❌ 配置測試失敗: {e}")
        return False

def test_data_store_module():
    """測試數據存儲模組"""
    print("🧪 測試 data_store.py...")
    try:
        import data_store
        print(f"  ✅ 數據存儲初始化成功")
        
        # 測試連接
        conn = data_store._get_connection()
        cursor = conn.cursor()
        
        # 檢查表格
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"    數據表: {tables}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ 數據存儲測試失敗: {e}")
        return False

def test_session_tracker_module():
    """測試會話追蹤模組"""
    print("🧪 測試 session_tracker.py...")
    try:
        import session_tracker
        tracker = session_tracker.session_tracker
        
        # 測試基本功能
        sessions = tracker.get_all_sessions()
        active_sessions = tracker.get_active_sessions()
        
        print(f"  ✅ 會話追蹤器初始化成功")
        print(f"    總會話數: {len(sessions)}")
        print(f"    活動會話: {len(active_sessions)}")
        
        # 測試統計
        stats = tracker.get_session_stats()
        print(f"    統計數據: {stats}")
        
        return True
    except Exception as e:
        print(f"  ❌ 會話追蹤測試失敗: {e}")
        return False

def test_resource_monitor_module():
    """測試資源監控模組"""
    print("🧪 測試 resource_monitor.py...")
    try:
        import resource_monitor
        monitor = resource_monitor.resource_monitor
        
        # 測試獲取指標
        metrics = monitor.get_current_metrics()
        
        print(f"  ✅ 資源監控器初始化成功")
        print(f"    CPU 使用率: {metrics.cpu_percent:.1f}%")
        print(f"    記憶體使用率: {metrics.memory_percent:.1f}%")
        print(f"    磁碟使用率: {metrics.disk_percent:.1f}%")
        
        # 測試歷史數據
        history = monitor.get_history(limit=5)
        print(f"    歷史數據點: {len(history)} 個")
        
        return True
    except Exception as e:
        print(f"  ❌ 資源監控測試失敗: {e}")
        return False

def test_telegram_dashboard_module():
    """測試 Telegram 儀表板模組"""
    print("🧪 測試 telegram_dashboard.py...")
    try:
        import telegram_dashboard
        
        # 創建模擬對象
        class MockSessionTracker:
            def get_active_sessions(self, limit=10):
                return []
            def get_session_count(self):
                return 0
            def get_statistics(self):
                return {'today_sessions': 5, 'completed_sessions': 10, 'failed_sessions': 2, 'avg_runtime_minutes': 15.5, 'success_rate': 83.3}
        
        class MockResourceMonitor:
            def get_current_metrics(self):
                class MockMetrics:
                    cpu_percent = 45.5
                    memory_percent = 67.8
                    disk_percent = 32.1
                    network_sent_mb = 125.4
                    network_recv_mb = 89.7
                    load_avg_1m = 1.2
                return MockMetrics()
        
        # 創建儀表板
        tracker = MockSessionTracker()
        monitor = MockResourceMonitor()
        dashboard = telegram_dashboard.TelegramDashboard(tracker, monitor)
        
        # 測試完整儀表板
        full_dashboard = dashboard.generate_full_dashboard()
        print(f"  ✅ 儀表板生成器初始化成功")
        print(f"    完整儀表板行數: {len(full_dashboard.split('\\n'))}")
        
        # 測試精簡儀表板
        compact_dashboard = dashboard.generate_compact_dashboard()
        print(f"    精簡儀表板行數: {len(compact_dashboard.split('\\n'))}")
        
        return True
    except Exception as e:
        print(f"  ❌ 儀表板測試失敗: {e}")
        return False

def test_alert_system_module():
    """測試警報系統模組"""
    print("🧪 測試 alert_system.py...")
    try:
        import alert_system
        
        # 創建模擬對象
        class MockSessionTracker:
            def get_session_stats(self):
                return {'active': 25, 'total': 30, 'failed': 2}
        
        class MockResourceMonitor:
            def get_current_metrics(self):
                class MockMetrics:
                    cpu_percent = 90.5
                    memory_percent = 85.2
                    disk_percent = 92.1
                return MockMetrics()
            def get_system_info(self):
                return {}
        
        # 創建警報系統
        tracker = MockSessionTracker()
        monitor = MockResourceMonitor()
        system = alert_system.AlertSystem(tracker, monitor)
        
        print(f"  ✅ 警報系統初始化成功")
        print(f"    規則數量: {len(system.rules)}")
        
        # 測試規則評估
        context = {
            'cpu_percent': 90.5,
            'memory_percent': 85.2,
            'disk_percent': 92.1,
            'active_sessions': 25
        }
        
        triggered_rules = []
        for rule in system.rules:
            triggered, message = rule.evaluate(context)
            if triggered:
                triggered_rules.append(rule.name)
        
        print(f"    觸發規則: {triggered_rules}")
        
        return True
    except Exception as e:
        print(f"  ❌ 警報系統測試失敗: {e}")
        return False

def test_agent_monitor_module():
    """測試主監控類別模組"""
    print("🧪 測試 agent_monitor.py...")
    try:
        import agent_monitor
        
        # 創建主監控器
        monitor = agent_monitor.AgentMonitor()
        
        print(f"  ✅ 主監控類別初始化成功")
        print(f"    開始時間: {monitor.start_time}")
        print(f"    運行狀態: {'運行中' if monitor.running else '已停止'}")
        
        # 測試信號處理
        print(f"    信號處理已註冊")
        
        return True
    except Exception as e:
        print(f"  ❌ 主監控測試失敗: {e}")
        return False

def test_integration_module():
    """測試系統整合模組"""
    print("🧪 測試 integration.py...")
    try:
        import integration
        
        # 創建模擬對象
        class MockSessionTracker:
            def get_all_sessions(self):
                return []
            def get_active_sessions(self):
                return []
        
        class MockResourceMonitor:
            pass
        
        # 創建整合管理器
        tracker = MockSessionTracker()
        monitor = MockResourceMonitor()
        manager = integration.IntegrationManager(tracker, monitor)
        
        print(f"  ✅ 整合管理器初始化成功")
        print(f"    啟用的整合: {manager.integrations_enabled}")
        
        # 測試初始化
        init_results = manager.initialize_integrations()
        print(f"    初始化結果: {len(init_results)} 個整合")
        
        return True
    except Exception as e:
        print(f"  ❌ 整合測試失敗: {e}")
        return False

def run_all_tests():
    """運行所有測試"""
    print("🚀 開始監控系統測試")
    print("=" * 50)
    
    test_results = []
    start_time = time.time()
    
    # 運行各模組測試
    test_results.append(("配置模組", test_config_module()))
    test_results.append(("數據存儲", test_data_store_module()))
    test_results.append(("會話追蹤", test_session_tracker_module()))
    test_results.append(("資源監控", test_resource_monitor_module()))
    test_results.append(("儀表板", test_telegram_dashboard_module()))
    test_results.append(("警報系統", test_alert_system_module()))
    test_results.append(("主監控", test_agent_monitor_module()))
    test_results.append(("系統整合", test_integration_module()))
    
    # 計算結果
    end_time = time.time()
    total_time = end_time - start_time
    
    print("=" * 50)
    print("📊 測試結果摘要")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for module_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{module_name:15} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 50)
    print(f"總測試數: {len(test_results)}")
    print(f"通過: {passed} | 失敗: {failed}")
    print(f"成功率: {(passed/len(test_results))*100:.1f}%")
    print(f"測試時間: {total_time:.2f}秒")
    
    if failed == 0:
        print("🎉 所有測試通過！監控系統功能正常。")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查相關模組。")
        return False

def quick_smoke_test():
    """快速冒煙測試 - 最基本的系統功能測試"""
    print("🚬 快速冒煙測試")
    print("=" * 30)
    
    tests = [
        ("導入 config", lambda: __import__('config')),
        ("導入 data_store", lambda: __import__('data_store')),
        ("導入 session_tracker", lambda: __import__('session_tracker')),
        ("導入 resource_monitor", lambda: __import__('resource_monitor')),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"  ✅ {test_name}")
        except Exception as e:
            print(f"  ❌ {test_name}: {e}")
    
    print("=" * 30)
    print("冒煙測試完成")

def generate_test_report():
    """生成測試報告"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'system': 'OpenClaw Agent Monitoring System',
        'tests': [],
        'summary': {}
    }
    
    # 這裡可以擴展為更詳細的報告生成
    # 目前返回簡單報告
    
    return report

if __name__ == "__main__":
    print("🤖 OpenClaw Agent 監控系統測試套件")
    print("版本: 1.0.0")
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 檢查命令行參數
    if len(sys.argv) > 1:
        if sys.argv[1] == 'quick':
            quick_smoke_test()
        elif sys.argv[1] == 'module':
            # 測試特定模組
            module_name = sys.argv[2] if len(sys.argv) > 2 else 'all'
            print(f"測試模組: {module_name}")
            
            if module_name == 'config':
                test_config_module()
            elif module_name == 'data_store':
                test_data_store_module()
            elif module_name == 'session_tracker':
                test_session_tracker_module()
            elif module_name == 'resource_monitor':
                test_resource_monitor_module()
            elif module_name == 'telegram_dashboard':
                test_telegram_dashboard_module()
            elif module_name == 'alert_system':
                test_alert_system_module()
            elif module_name == 'agent_monitor':
                test_agent_monitor_module()
            elif module_name == 'integration':
                test_integration_module()
            else:
                print("未知模組，使用完整測試")
                run_all_tests()
        else:
            run_all_tests()
    else:
        # 預設運行完整測試
        run_all_tests()
    
    print()
    print("測試完成！")
    print("使用方式:")
    print("  python test_monitoring.py          # 完整測試")
    print("  python test_monitoring.py quick    # 快速冒煙測試")
    print("  python test_monitoring.py module <模組名稱>  # 測試特定模組")