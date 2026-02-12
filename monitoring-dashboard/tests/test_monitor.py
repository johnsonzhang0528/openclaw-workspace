#!/usr/bin/env python3
"""
監控儀表板測試腳本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor_bot import SubagentMonitor
from telegram_integration import TelegramMonitorBot

def test_monitor_bot():
    """測試監控機器人"""
    print("🧪 測試監控機器人...")
    
    monitor = SubagentMonitor()
    
    # 測試精簡模式
    print("\n📊 測試精簡模式:")
    compact = monitor.generate_compact_dashboard()
    print(compact)
    
    # 測試詳細模式
    print("\n📋 測試詳細模式:")
    detailed = monitor.generate_detailed_dashboard()
    print(detailed)
    
    # 測試圖表模式
    print("\n📈 測試圖表模式:")
    chart = monitor.generate_chart_dashboard()
    print(chart)
    
    print("✅ 監控機器人測試完成")

def test_telegram_bot():
    """測試 Telegram 機器人"""
    print("\n🧪 測試 Telegram 機器人...")
    
    bot = TelegramMonitorBot()
    
    # 測試幫助訊息
    print("\n📚 測試幫助訊息:")
    help_msg = bot.get_help_message()
    print(help_msg)
    
    # 測試回調處理
    print("\n🔄 測試回調處理:")
    
    test_callbacks = [
        "monitor_compact",
        "monitor_detailed",
        "monitor_chart",
        "monitor_refresh",
        "monitor_alerts",
        "monitor_history",
        "task_pause_abc123",
        "task_resume_abc123",
        "task_stop_abc123"
    ]
    
    for callback in test_callbacks:
        print(f"\n測試回調: {callback}")
        result = bot.handle_callback(callback)
        print(f"模式: {result['mode']}")
        print(f"文字長度: {len(result['text'])} 字元")
        if result['keyboard']:
            print(f"鍵盤按鈕: {len(result['keyboard'])} 行")
    
    print("✅ Telegram 機器人測試完成")

def test_system_info():
    """測試系統資訊獲取"""
    print("\n🧪 測試系統資訊獲取...")
    
    monitor = SubagentMonitor()
    
    # 獲取系統資訊
    system_info = monitor.get_system_info()
    print(f"系統資訊: {system_info}")
    
    # 測試時間格式化
    test_timestamps = [
        0,
        int(time.time() * 1000) - 30000,  # 30秒前
        int(time.time() * 1000) - 180000,  # 3分鐘前
        int(time.time() * 1000) - 3600000,  # 1小時前
        int(time.time() * 1000) - 86400000,  # 1天前
    ]
    
    print("\n⏰ 測試時間格式化:")
    for ts in test_timestamps:
        formatted = monitor.format_timestamp(ts)
        print(f"{ts} -> {formatted}")
    
    print("✅ 系統資訊測試完成")

def test_progress_bar():
    """測試進度條生成"""
    print("\n🧪 測試進度條生成...")
    
    monitor = SubagentMonitor()
    
    test_progress = [0, 25, 50, 75, 100, 33.3, 66.6, 99.9]
    
    for progress in test_progress:
        bar = monitor.generate_progress_bar(progress)
        print(f"{progress:5.1f}%: {bar}")
    
    print("✅ 進度條測試完成")

if __name__ == "__main__":
    import time
    
    print("🚀 開始監控儀表板測試套件")
    print("=" * 50)
    
    try:
        test_monitor_bot()
        test_telegram_bot()
        test_system_info()
        test_progress_bar()
        
        print("\n" + "=" * 50)
        print("🎉 所有測試完成！")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)