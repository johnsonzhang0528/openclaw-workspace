#!/usr/bin/env python3
"""
測試 Telegram API 連接和通知功能
"""

import requests
import os
import sys
from dotenv import load_dotenv

def test_telegram_connection():
    """測試 Telegram API 連接"""
    print("🔗 測試 Telegram API 連接...")
    
    # 載入環境變數
    load_dotenv()
    
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Telegram 配置不完整")
        return False
    
    # 測試 1: 獲取 Bot 資訊
    print("\n1. 測試 Bot 資訊獲取...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_data = bot_info['result']
                print(f"   ✅ Bot 資訊獲取成功")
                print(f"     名稱: {bot_data.get('first_name', 'N/A')}")
                print(f"     使用者名稱: @{bot_data.get('username', 'N/A')}")
                print(f"     Bot ID: {bot_data.get('id', 'N/A')}")
            else:
                print(f"   ❌ API 回應錯誤: {bot_info.get('description', 'Unknown error')}")
                return False
        else:
            print(f"   ❌ HTTP 錯誤: {response.status_code}")
            print(f"     回應: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ 連接失敗: {e}")
        return False
    
    # 測試 2: 發送測試訊息
    print("\n2. 測試訊息發送...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    test_message = """
🤖 <b>OpenClaw 監控系統測試通知</b>
──────────────────────────────
✅ <b>系統狀態</b>: 正常
📅 <b>測試時間</b>: 系統初始化完成
🔧 <b>功能測試</b>: Telegram 通知功能
──────────────────────────────
<i>這是一則測試訊息，確認監控系統的 Telegram 通知功能正常運作。</i>
"""
    
    payload = {
        'chat_id': CHAT_ID,
        'text': test_message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
        'disable_notification': False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                message_data = result['result']
                print(f"   ✅ 測試訊息發送成功")
                print(f"     訊息 ID: {message_data.get('message_id', 'N/A')}")
                print(f"     發送時間: {message_data.get('date', 'N/A')}")
                print(f"     聊天: {message_data.get('chat', {}).get('title', 'Private Chat')}")
            else:
                print(f"   ❌ 訊息發送失敗: {result.get('description', 'Unknown error')}")
                return False
        else:
            print(f"   ❌ HTTP 錯誤: {response.status_code}")
            print(f"     回應: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ 訊息發送失敗: {e}")
        return False
    
    # 測試 3: 測試監控系統儀表板
    print("\n3. 測試監控系統儀表板生成...")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import telegram_dashboard
        
        # 創建模擬對象
        class MockSessionTracker:
            def get_active_sessions(self, limit=10):
                return [
                    {
                        'id': 'test-session-001',
                        'name': '系統初始化任務',
                        'status': 'COMPLETED',
                        'progress': 100.0,
                        'start_time': '2026-02-12 13:30:00',
                        'estimated_completion': '2026-02-12 13:35:00'
                    }
                ]
            
            def get_session_count(self):
                return {'total': 1, 'active': 0, 'completed': 1, 'failed': 0}
            
            def get_statistics(self):
                return {
                    'today_sessions': 1,
                    'completed_sessions': 1,
                    'failed_sessions': 0,
                    'avg_runtime_minutes': 5.0,
                    'success_rate': 100.0
                }
        
        class MockResourceMonitor:
            def get_current_metrics(self):
                class MockMetrics:
                    cpu_percent = 12.5
                    memory_percent = 34.2
                    disk_percent = 28.7
                    network_sent_mb = 45.3
                    network_recv_mb = 32.1
                    load_avg_1m = 0.8
                return MockMetrics()
        
        tracker = MockSessionTracker()
        monitor = MockResourceMonitor()
        dashboard = telegram_dashboard.TelegramDashboard(tracker, monitor)
        
        # 生成儀表板
        dashboard_html = dashboard.generate_full_dashboard()
        
        print(f"   ✅ 儀表板生成成功")
        print(f"     長度: {len(dashboard_html)} 字元")
        print(f"     行數: {dashboard_html.count('\\n') + 1}")
        
        # 檢查儀表板內容
        if 'OpenClaw Agent 監控儀表板' in dashboard_html:
            print(f"   ✅ 儀表板標題正確")
        if '系統資源監控' in dashboard_html:
            print(f"   ✅ 資源監控部分正常")
        if '系統統計' in dashboard_html:
            print(f"   ✅ 系統統計部分正常")
        
    except Exception as e:
        print(f"   ❌ 儀表板生成失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("🎉 所有 Telegram 測試通過！")
    print("=" * 50)
    return True

def send_monitoring_start_notification():
    """發送監控系統啟動通知"""
    print("\n📢 發送監控系統啟動通知...")
    
    load_dotenv()
    
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    start_message = """
🚀 <b>OpenClaw Agent 監控系統已啟動</b>
──────────────────────────────
✅ <b>系統狀態</b>: 運行中
🕐 <b>啟動時間</b>: 系統初始化完成
📊 <b>監控功能</b>: 已啟用
🔔 <b>通知頻道</b>: Telegram
──────────────────────────────
<b>監控項目:</b>
• 📈 系統資源 (CPU/記憶體/磁碟)
• 🤖 Agent 會話狀態
• 🚨 智能警報系統
• 📱 即時儀表板更新

<b>監控間隔:</b> 每30秒
<b>警報閾值:</b> CPU 80%, 記憶體 85%, 磁碟 90%

<i>系統將定期發送監控報告和警報通知。</i>
"""
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': start_message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
        'disable_notification': False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ 啟動通知發送成功")
                return True
            else:
                print(f"❌ 啟動通知發送失敗: {result.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP 錯誤: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 啟動通知發送失敗: {e}")
        return False

if __name__ == "__main__":
    print("🤖 OpenClaw Agent 監控系統 - Telegram 整合測試")
    print("=" * 60)
    
    # 測試連接
    if test_telegram_connection():
        # 發送啟動通知
        send_monitoring_start_notification()
        print("\n✅ Telegram 整合測試完成，系統已準備就緒！")
        sys.exit(0)
    else:
        print("\n❌ Telegram 整合測試失敗，請檢查配置")
        sys.exit(1)