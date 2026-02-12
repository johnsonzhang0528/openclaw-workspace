#!/usr/bin/env python3
"""
Telegram 監控儀表板演示
展示如何在 Telegram 中使用監控技能
"""

from telegram_integration import TelegramMonitorBot

def demonstrate_telegram_integration():
    """演示 Telegram 整合功能"""
    
    print("🤖 Telegram 監控儀表板演示")
    print("=" * 60)
    
    bot = TelegramMonitorBot()
    
    # 1. 顯示幫助訊息
    print("\n1. 📚 幫助訊息演示:")
    print("-" * 40)
    help_msg = bot.get_help_message()
    print(help_msg)
    
    # 2. 顯示精簡模式
    print("\n2. 📊 精簡模式演示:")
    print("-" * 40)
    compact_dashboard = bot.monitor.generate_compact_dashboard()
    print(compact_dashboard)
    
    # 3. 顯示詳細模式
    print("\n3. 📋 詳細模式演示:")
    print("-" * 40)
    detailed_dashboard = bot.monitor.generate_detailed_dashboard()
    print(detailed_dashboard[:500] + "...")  # 只顯示前500字元
    
    # 4. 顯示圖表模式
    print("\n4. 📈 圖表模式演示:")
    print("-" * 40)
    chart_dashboard = bot.monitor.generate_chart_dashboard()
    print(chart_dashboard)
    
    # 5. 演示 inline keyboard
    print("\n5. 🎮 Inline Keyboard 演示:")
    print("-" * 40)
    
    modes = ["compact", "detailed", "chart"]
    for mode in modes:
        keyboard = bot.generate_inline_keyboard(mode)
        print(f"\n{mode} 模式鍵盤 ({len(keyboard)} 行):")
        for row in keyboard:
            buttons = [f"{btn['text']} ({btn['callback_data']})" for btn in row]
            print(f"  {', '.join(buttons)}")
    
    # 6. 演示回調處理
    print("\n6. 🔄 回調處理演示:")
    print("-" * 40)
    
    test_callbacks = [
        "monitor_compact",
        "monitor_detailed",
        "monitor_chart",
        "monitor_refresh",
        "monitor_alerts",
        "monitor_history",
        "task_pause_abc123def",
        "task_resume_abc123def",
        "task_stop_abc123def"
    ]
    
    for callback in test_callbacks:
        result = bot.handle_callback(callback)
        print(f"\n回調: {callback}")
        print(f"  模式: {result['mode']}")
        print(f"  文字長度: {len(result['text'])} 字元")
        if result['keyboard']:
            print(f"  鍵盤行數: {len(result['keyboard'])}")
    
    # 7. 演示控制鍵盤
    print("\n7. 🎛️ 任務控制鍵盤演示:")
    print("-" * 40)
    
    task_id = "test_task_123"
    control_keyboard = bot.generate_control_keyboard(task_id)
    print(f"任務控制鍵盤 ({len(control_keyboard)} 行):")
    for row in control_keyboard:
        buttons = [f"{btn['text']} ({btn['callback_data']})" for btn in row]
        print(f"  {', '.join(buttons)}")
    
    print("\n" + "=" * 60)
    print("🎉 Telegram 整合演示完成！")
    print("\n📋 實際使用時，這些功能會通過 Telegram Bot 提供：")
    print("   • 用戶輸入 /monitor 顯示儀表板")
    print("   • 點擊 inline buttons 切換模式/控制任務")
    print("   • 系統自動更新監控數據")
    print("   • 警報系統自動通知")

def main():
    """主函數"""
    try:
        demonstrate_telegram_integration()
    except Exception as e:
        print(f"❌ 演示失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()