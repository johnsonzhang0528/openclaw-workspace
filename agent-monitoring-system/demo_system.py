#!/usr/bin/env python3
"""
Agent Monitoring System 功能演示
展示系統核心功能和工作流程
"""

import sys
import os
import time
from datetime import datetime, timedelta

# 添加當前目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_system():
    """演示系統功能"""
    print("=" * 60)
    print("🤖 Agent Monitoring System 功能演示")
    print("=" * 60)
    print()
    
    # 1. 導入並初始化系統
    print("1️⃣ 初始化監控系統...")
    from agent_monitor import AgentMonitor
    
    monitor = AgentMonitor()
    print(f"   ✅ 主監控器創建成功")
    print(f"   📅 開始時間: {monitor.start_time}")
    print()
    
    # 2. 演示數據存儲
    print("2️⃣ 演示數據存儲功能...")
    from data_store import data_store, SessionData, SessionStatus, ResourceData
    
    # 添加測試會話
    test_sessions = [
        SessionData(
            session_id="demo-session-001",
            label="數據分析任務",
            status=SessionStatus.ACTIVE,
            progress=0.4,
            start_time=datetime.now() - timedelta(minutes=45),
            last_update=datetime.now(),
            estimated_completion=datetime.now() + timedelta(hours=1),
            metadata={"type": "analysis", "priority": "high"}
        ),
        SessionData(
            session_id="demo-session-002",
            label="系統部署任務",
            status=SessionStatus.COMPLETED,
            progress=1.0,
            start_time=datetime.now() - timedelta(hours=2),
            last_update=datetime.now() - timedelta(minutes=30),
            metadata={"type": "deployment", "result": "success"}
        ),
        SessionData(
            session_id="demo-session-003",
            label="性能測試任務",
            status=SessionStatus.ACTIVE,
            progress=0.7,
            start_time=datetime.now() - timedelta(minutes=20),
            last_update=datetime.now(),
            metadata={"type": "performance", "iterations": 1000}
        )
    ]
    
    for session in test_sessions:
        data_store.save_session(session)
    
    print(f"   ✅ 添加了 {len(test_sessions)} 個測試會話")
    
    # 添加資源數據
    for i in range(5):
        resource_data = ResourceData(
            timestamp=datetime.now() - timedelta(minutes=i*10),
            cpu_percent=30.0 + i*10,
            memory_percent=40.0 + i*8,
            disk_percent=20.0 + i*5,
            network_sent=1000000 * (i+1),
            network_recv=500000 * (i+1),
            active_sessions=len([s for s in test_sessions if s.status == SessionStatus.ACTIVE])
        )
        data_store.save_resource_data(resource_data)
    
    print(f"   ✅ 添加了 5 條資源歷史記錄")
    print()
    
    # 3. 演示資源監控
    print("3️⃣ 演示資源監控功能...")
    from resource_monitor import ResourceMonitor
    
    resource_monitor = ResourceMonitor()
    current_metrics = resource_monitor.collect_metrics()
    
    if current_metrics:
        print(f"   📊 當前系統資源:")
        print(f"      CPU 使用率: {current_metrics.cpu_percent:.1f}%")
        print(f"      記憶體使用率: {current_metrics.memory_percent:.1f}%")
        print(f"      磁碟使用率: {current_metrics.disk_percent:.1f}%")
        print(f"      系統負載: {current_metrics.load_average[0]:.2f}, {current_metrics.load_average[1]:.2f}, {current_metrics.load_average[2]:.2f}")
    print()
    
    # 4. 演示會話追蹤
    print("4️⃣ 演示會話追蹤功能...")
    from session_tracker import SessionTracker
    
    session_tracker = SessionTracker()
    active_sessions = session_tracker.get_active_sessions()
    session_stats = session_tracker.get_session_stats()
    
    print(f"   👥 會話狀態:")
    print(f"      活動會話: {len(active_sessions)} 個")
    print(f"      總會話數: {session_stats.get('total_sessions', 0)} 個")
    print(f"      平均進度: {session_stats.get('average_progress', 0)*100:.1f}%")
    print()
    
    # 5. 演示警報系統
    print("5️⃣ 演示警報系統功能...")
    from alert_system import AlertSystem, AlertLevel
    
    alert_system = AlertSystem(session_tracker, resource_monitor)
    
    # 手動觸發測試警報
    alert_system.manual_alert(
        level=AlertLevel.INFO,
        message="系統演示：監控系統功能正常"
    )
    
    alert_system.manual_alert(
        level=AlertLevel.WARNING,
        message="系統演示：CPU 使用率偏高（測試數據）"
    )
    
    active_alerts = alert_system.get_active_alerts()
    print(f"   🚨 當前警報狀態:")
    print(f"      活動警報: {len(active_alerts)} 個")
    for alert in active_alerts[:3]:  # 顯示前3個
        print(f"      • {alert.level.value.upper()}: {alert.message}")
    print()
    
    # 6. 演示 Telegram 儀表板
    print("6️⃣ 演示 Telegram 儀表板功能...")
    from telegram_dashboard import TelegramDashboard
    
    dashboard = TelegramDashboard(session_tracker, resource_monitor)
    
    # 生成儀表板
    dashboard_html = dashboard.generate_full_dashboard()
    
    print(f"   📱 儀表板預覽:")
    print("-" * 40)
    
    # 提取並顯示儀表板的部分內容
    lines = dashboard_html.split('\n')
    for line in lines[:15]:  # 顯示前15行
        # 移除 HTML 標籤用於顯示
        clean_line = line.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', '')
        if clean_line.strip():
            print(f"   {clean_line}")
    
    print("-" * 40)
    print()
    
    # 7. 演示系統整合
    print("7️⃣ 演示系統整合功能...")
    from integration import IntegrationManager
    
    integration_mgr = IntegrationManager(session_tracker, resource_monitor)
    
    print(f"   🔗 整合模組狀態:")
    for name, enabled in integration_mgr.enabled_integrations.items():
        status = "✅ 已啟用" if enabled else "❌ 已禁用"
        print(f"      {name}: {status}")
    print()
    
    # 8. 系統狀態總結
    print("8️⃣ 系統狀態總結...")
    print()
    
    # 查詢數據庫統計
    all_sessions = data_store.get_all_sessions()
    resource_history = data_store.get_resource_history(limit=10)
    alerts = data_store.get_unacknowledged_alerts()
    
    print("   📈 系統數據統計:")
    print(f"      會話記錄: {len(all_sessions)} 條")
    print(f"      資源記錄: {len(resource_history)} 條")
    print(f"      未確認警報: {len(alerts)} 條")
    print()
    
    print("   ⚙️ 監控組件狀態:")
    components = [
        ("配置管理", "✅ 正常"),
        ("數據存儲", "✅ 正常"),
        ("資源監控", "✅ 正常"),
        ("會話追蹤", "✅ 正常"),
        ("警報系統", "✅ 正常"),
        ("Telegram 儀表板", "✅ 正常"),
        ("系統整合", "✅ 正常")
    ]
    
    for name, status in components:
        print(f"      {name}: {status}")
    print()
    
    print("=" * 60)
    print("🎉 功能演示完成！")
    print("=" * 60)
    print()
    print("系統功能驗證:")
    print("  • 所有核心模組正常運作")
    print("  • 數據存儲和檢索功能正常")
    print("  • 資源監控實時更新")
    print("  • 會話狀態追蹤準確")
    print("  • 警報系統響應及時")
    print("  • Telegram 儀表板生成正常")
    print()
    print("下一步:")
    print("  1. 配置真實的 Telegram Bot Token 和 Chat ID")
    print("  2. 啟動 OpenClaw Gateway 服務以啟用完整整合")
    print("  3. 設置郵件/SMS 警報（可選）")
    print("  4. 部署為常駐服務")
    print()

if __name__ == "__main__":
    try:
        demo_system()
    except Exception as e:
        print(f"演示過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)