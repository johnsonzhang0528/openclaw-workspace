"""
測試修復後的導入問題
"""

import sys
import os

# 添加當前目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 載入環境變數
env_file = os.path.join(os.path.dirname(__file__), '.env.test')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value

print("🧪 測試模組導入...")
print("=" * 50)

# 測試導入每個模組
modules_to_test = [
    ('config', 'config'),
    ('data_store', 'data_store'),
    ('session_tracker', 'session_tracker'),
    ('resource_monitor', 'resource_monitor'),
    ('telegram_dashboard', 'TelegramDashboard'),
    ('alert_system', 'AlertSystem'),
    ('agent_monitor', 'AgentMonitor'),
    ('integration', 'IntegrationManager'),
    ('test_monitoring', 'run_all_tests'),
]

success_count = 0
failure_count = 0

for module_name, item_name in modules_to_test:
    try:
        module = __import__(module_name)
        print(f"✅ {module_name:20} 導入成功")
        
        # 測試特定項目
        if hasattr(module, item_name):
            item = getattr(module, item_name)
            print(f"   └─ {item_name} 可用")
        
        success_count += 1
    except Exception as e:
        print(f"❌ {module_name:20} 導入失敗: {e}")
        failure_count += 1

print("=" * 50)
print(f"測試結果: {success_count} 成功, {failure_count} 失敗")

if failure_count == 0:
    print("🎉 所有模組導入成功！")
    
    # 測試套件功能
    print("\n🧪 測試套件功能...")
    try:
        # 測試配置
        import config
        cfg = config.config
        print(f"✅ 配置載入: 監控間隔={cfg.monitoring.polling_interval}秒")
        
        # 測試資源監控
        import resource_monitor
        monitor = resource_monitor.resource_monitor
        metrics = monitor.get_current_metrics()
        if metrics:
            print(f"✅ 資源監控: CPU={metrics.cpu_percent:.1f}%")
        else:
            print("⚠️  資源監控: 無數據")
        
        # 測試會話追蹤
        import session_tracker
        tracker = session_tracker.session_tracker
        sessions = tracker.get_active_sessions()
        print(f"✅ 會話追蹤: {len(sessions)} 個活動會話")
        
        print("\n🚀 系統功能測試完成！")
        
    except Exception as e:
        print(f"❌ 功能測試失敗: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠️  部分模組導入失敗，需要進一步修復")