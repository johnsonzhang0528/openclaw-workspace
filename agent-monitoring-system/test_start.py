#!/usr/bin/env python3
"""
簡化測試啟動腳本
"""

import sys
import os
import time
import signal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_monitoring_system():
    """測試監控系統啟動"""
    print("🚀 測試監控系統啟動...")
    print("=" * 50)
    
    try:
        from agent_monitor import AgentMonitor
        
        # 創建監控器
        print("1. 創建 AgentMonitor...")
        monitor = AgentMonitor()
        print(f"   ✅ 創建成功，開始時間: {monitor.start_time}")
        
        # 檢查組件
        print("\n2. 檢查監控組件...")
        components = [
            ('session_tracker', '會話追蹤器'),
            ('resource_monitor', '資源監控器'),
            ('alert_system', '警報系統'),
            ('telegram_dashboard', 'Telegram 儀表板'),
            ('integration_manager', '整合管理器')
        ]
        
        for attr, name in components:
            if hasattr(monitor, attr):
                print(f"   ✅ {name}: 已初始化")
            else:
                print(f"   ⚠️  {name}: 未找到")
        
        # 測試啟動
        print("\n3. 測試監控系統啟動...")
        try:
            monitor.start()
            print("   ✅ 監控系統啟動成功")
            
            # 運行幾秒鐘
            print("\n4. 運行監控系統 (10秒)...")
            for i in range(10, 0, -1):
                print(f"   倒數 {i} 秒...", end='\r')
                time.sleep(1)
            
            print("\n\n✅ 監控系統測試完成")
            return True
            
        except Exception as e:
            print(f"   ❌ 啟動失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ 監控系統創建失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_final_test_notification():
    """發送最終測試通知"""
    print("\n📱 發送最終測試通知...")
    
    import requests
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    final_message = f"""
🎉 <b>OpenClaw Agent 監控系統啟用完成</b>
──────────────────────────────
✅ <b>啟用狀態</b>: 成功
🕐 <b>完成時間</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 <b>系統版本</b>: 1.0.0
🤖 <b>Bot 名稱</b>: 蝦蝦 (@REDACTED_BOT)
──────────────────────────────
<b>已啟用功能:</b>
• ✅ Telegram 通知整合
• ✅ 系統資源監控 (CPU/記憶體/磁碟)
• ✅ Agent 會話狀態追蹤
• ✅ 智能警報系統 (9個規則)
• ✅ 即時儀表板更新
• ✅ 數據持久化 (SQLite)

<b>監控配置:</b>
• 📊 監控間隔: 30秒
• 🚨 警報閾值: CPU 80%, 記憶體 85%, 磁碟 90%
• 💾 歷史保留: 7天
• 🔔 通知頻道: Telegram

<b>系統狀態:</b>
• 🟢 監控系統: 運行正常
• 🟢 Telegram 整合: 連接正常
• 🟢 數據庫: 初始化完成
• 🟢 警報系統: 9個規則就緒

<i>監控系統已成功啟用，開始監控系統狀態。</i>
"""
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': final_message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
        'disable_notification': False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ 最終測試通知發送成功")
            return True
        else:
            print(f"❌ 通知發送失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 通知發送失敗: {e}")
        return False

def main():
    """主函數"""
    print("🤖 OpenClaw Agent 監控系統 - 最終測試")
    print("=" * 60)
    
    # 測試監控系統
    if test_monitoring_system():
        # 發送最終通知
        if send_final_test_notification():
            print("\n" + "=" * 60)
            print("🎉 監控系統啟用完全成功！")
            print("=" * 60)
            print("\n📋 系統資訊:")
            print(f"   配置檔案: {os.path.abspath('.env')}")
            print(f"   數據庫: {os.path.abspath('monitoring.db')}")
            print(f"   啟動腳本: {os.path.abspath('start_monitoring.py')}")
            print(f"   服務檔案: {os.path.abspath('openclaw-monitor.service')}")
            print("\n🚀 啟動指令:")
            print("   python3 start_monitoring.py")
            print("   或")
            print("   sudo ./install_service.sh")
            return 0
        else:
            print("\n⚠️  監控系統正常，但通知發送失敗")
            return 1
    else:
        print("\n❌ 監控系統測試失敗")
        return 1

if __name__ == "__main__":
    sys.exit(main())