#!/usr/bin/env python3
"""
Agent Monitoring System 部署測試腳本
測試系統核心功能而不依賴外部服務
"""

import sys
import os
import time
from datetime import datetime, timedelta

# 添加當前目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """測試配置模組"""
    print("🧪 測試配置模組...")
    try:
        from config import config
        print(f"  ✅ 配置載入成功")
        print(f"    監控間隔: {config.monitoring.polling_interval}秒")
        print(f"    Telegram Chat ID: {config.telegram.chat_id}")
        return True
    except Exception as e:
        print(f"  ❌ 配置測試失敗: {e}")
        return False

def test_data_store():
    """測試數據存儲"""
    print("🧪 測試數據存儲...")
    try:
        from data_store import data_store, SessionData, SessionStatus
        from datetime import datetime
        
        # 測試添加會話
        test_session = SessionData(
            session_id="deployment-test-001",
            label="部署測試會話",
            status=SessionStatus.ACTIVE,
            progress=0.75,
            start_time=datetime.now() - timedelta(minutes=45),
            last_update=datetime.now(),
            metadata={"test": "deployment", "priority": "high"}
        )
        
        data_store.save_session(test_session)
        print(f"  ✅ 會話保存成功")
        
        # 測試查詢會話
        sessions = data_store.get_all_sessions()
        print(f"  ✅ 會話查詢成功: {len(sessions)} 個會話")
        
        # 測試資源數據
        from data_store import ResourceData
        resource_data = ResourceData(
            timestamp=datetime.now(),
            cpu_percent=45.5,
            memory_percent=67.8,
            disk_percent=32.1,
            network_sent=125400000,
            network_recv=89700000,
            active_sessions=3
        )
        
        data_store.save_resource_data(resource_data)
        print(f"  ✅ 資源數據保存成功")
        
        # 測試查詢資源歷史
        history = data_store.get_resource_history(limit=5)
        print(f"  ✅ 資源歷史查詢成功: {len(history)} 條記錄")
        
        return True
    except Exception as e:
        print(f"  ❌ 數據存儲測試失敗: {e}")
        return False

def test_resource_monitor():
    """測試資源監控"""
    print("🧪 測試資源監控...")
    try:
        from resource_monitor import ResourceMonitor
        
        monitor = ResourceMonitor()
        print(f"  ✅ 資源監控器創建成功")
        
        # 收集指標
        metrics = monitor.collect_metrics()
        if metrics:
            print(f"  ✅ 資源指標收集成功")
            print(f"    CPU: {metrics.cpu_percent:.1f}%")
            print(f"    記憶體: {metrics.memory_percent:.1f}%")
            print(f"    磁碟: {metrics.disk_percent:.1f}%")
            return True
        else:
            print(f"  ❌ 資源指標收集失敗")
            return False
    except Exception as e:
        print(f"  ❌ 資源監控測試失敗: {e}")
        return False

def test_session_tracker():
    """測試會話追蹤"""
    print("🧪 測試會話追蹤...")
    try:
        from session_tracker import SessionTracker
        
        tracker = SessionTracker()
        print(f"  ✅ 會話追蹤器創建成功")
        
        # 手動更新進度
        tracker.manual_update_progress(
            session_id="tracker-test-001",
            progress_percentage=50.0,
            current_step="部署測試"
        )
        print(f"  ✅ 會話進度更新成功")
        
        # 獲取活動會話
        sessions = tracker.get_active_sessions()
        print(f"  ✅ 活動會話查詢: {len(sessions)} 個會話")
        
        # 獲取會話統計
        stats = tracker.get_session_stats()
        print(f"  ✅ 會話統計獲取成功")
        print(f"    總會話數: {stats.get('total_sessions', 0)}")
        
        return True
    except Exception as e:
        print(f"  ❌ 會話追蹤測試失敗: {e}")
        return False

def test_alert_system():
    """測試警報系統"""
    print("🧪 測試警報系統...")
    try:
        from alert_system import AlertSystem, AlertLevel
        from session_tracker import SessionTracker
        from resource_monitor import ResourceMonitor
        
        # 創建依賴
        session_tracker_inst = SessionTracker()
        resource_monitor_inst = ResourceMonitor()
        
        # 創建警報系統
        alert_sys = AlertSystem(session_tracker_inst, resource_monitor_inst)
        print(f"  ✅ 警報系統創建成功")
        
        # 檢查規則
        print(f"    規則數量: {len(alert_sys.rules)}")
        
        # 手動觸發警報
        alert_sys.manual_alert(
            level=AlertLevel.WARNING,
            message="部署測試：系統功能正常"
        )
        print(f"  ✅ 手動警報觸發成功")
        
        # 獲取活動警報
        active_alerts = alert_sys.get_active_alerts()
        print(f"  ✅ 活動警報查詢: {len(active_alerts)} 個警報")
        
        return True
    except Exception as e:
        print(f"  ❌ 警報系統測試失敗: {e}")
        return False

def test_telegram_dashboard():
    """測試 Telegram 儀表板"""
    print("🧪 測試 Telegram 儀表板...")
    try:
        from telegram_dashboard import TelegramDashboard
        from session_tracker import SessionTracker
        from resource_monitor import ResourceMonitor
        
        # 創建依賴
        session_tracker_inst = SessionTracker()
        resource_monitor_inst = ResourceMonitor()
        
        # 創建儀表板
        dashboard = TelegramDashboard(session_tracker_inst, resource_monitor_inst)
        print(f"  ✅ Telegram 儀表板創建成功")
        
        # 生成儀表板
        dashboard_html = dashboard.generate_full_dashboard()
        print(f"  ✅ 儀表板生成成功")
        print(f"    內容長度: {len(dashboard_html)} 字元")
        
        # 檢查是否包含關鍵元素
        if "OpenClaw Agent 監控儀表板" in dashboard_html:
            print(f"  ✅ 儀表板標題正確")
        if "最後更新" in dashboard_html:
            print(f"  ✅ 時間戳記正確")
        
        return True
    except Exception as e:
        print(f"  ❌ Telegram 儀表板測試失敗: {e}")
        return False

def test_agent_monitor():
    """測試主監控系統"""
    print("🧪 測試主監控系統...")
    try:
        from agent_monitor import AgentMonitor
        
        # 創建主監控器
        monitor = AgentMonitor()
        print(f"  ✅ 主監控器創建成功")
        
        print(f"    開始時間: {monitor.start_time}")
        print(f"    運行狀態: {'運行中' if monitor.running else '已停止'}")
        print(f"    監控週期: {monitor.monitoring_cycles}")
        
        # 檢查組件
        components = [
            ("會話追蹤器", monitor.session_tracker),
            ("資源監控器", monitor.resource_monitor),
            ("警報系統", monitor.alert_system),
            ("Telegram 儀表板", monitor.dashboard),
            ("整合管理器", monitor.integration)
        ]
        
        for name, component in components:
            if component:
                print(f"    {name}: ✅ 已初始化")
            else:
                print(f"    {name}: ❌ 未初始化")
        
        return True
    except Exception as e:
        print(f"  ❌ 主監控系統測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("=" * 60)
    print("🤖 Agent Monitoring System 部署測試")
    print("=" * 60)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_results = []
    
    # 運行所有測試
    test_results.append(("配置模組", test_config()))
    test_results.append(("數據存儲", test_data_store()))
    test_results.append(("資源監控", test_resource_monitor()))
    test_results.append(("會話追蹤", test_session_tracker()))
    test_results.append(("警報系統", test_alert_system()))
    test_results.append(("Telegram 儀表板", test_telegram_dashboard()))
    test_results.append(("主監控系統", test_agent_monitor()))
    
    # 輸出測試結果
    print()
    print("=" * 60)
    print("📊 測試結果摘要")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print()
    print(f"總測試數: {len(test_results)}")
    print(f"通過: {passed} | 失敗: {failed}")
    print(f"成功率: {passed/len(test_results)*100:.1f}%")
    
    if failed == 0:
        print()
        print("🎉 所有測試通過！系統部署成功！")
        print()
        print("系統功能摘要:")
        print("  • 配置管理: ✅ 正常")
        print("  • 數據存儲: ✅ 正常")
        print("  • 資源監控: ✅ 正常")
        print("  • 會話追蹤: ✅ 正常")
        print("  • 警報系統: ✅ 正常")
        print("  • Telegram 儀表板: ✅ 正常")
        print("  • 主監控系統: ✅ 正常")
        print()
        print("⚠️  注意事項:")
        print("  • Telegram 通知需要有效的 Bot Token 和 Chat ID")
        print("  • OpenClaw 整合需要運行中的 Gateway 服務")
        print("  • 郵件/SMS 警報需要額外配置")
    else:
        print()
        print("⚠️  部分測試失敗，需要進一步檢查和修復")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)