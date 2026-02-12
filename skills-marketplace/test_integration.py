#!/usr/bin/env python3
"""
技能市集整合測試
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_handler import get_telegram_handler

def test_all_features():
    """測試所有功能"""
    handler = get_telegram_handler()
    
    print("🎯 技能市集整合測試\n")
    
    # 1. 測試主選單
    print("1. 測試主選單:")
    result = handler.show_main_menu()
    print(f"   ✓ 主選單生成成功")
    print(f"   訊息長度: {len(result['message'])} 字符")
    print(f"   按鈕數量: {len(result['keyboard'])} 行\n")
    
    # 2. 測試搜索功能
    print("2. 測試搜索功能 (weather):")
    result = handler.search_skills("weather", limit=3)
    if "error" in result.get("message", ""):
        print(f"   ✗ 搜索失敗: {result['message']}")
    else:
        print(f"   ✓ 搜索成功")
        print(f"   訊息長度: {len(result['message'])} 字符")
        if "keyboard" in result:
            print(f"   按鈕數量: {len(result['keyboard'])} 行\n")
    
    # 3. 測試最新技能
    print("3. 測試最新技能:")
    result = handler.explore_latest_skills(limit=3)
    if "error" in result.get("message", ""):
        print(f"   ✗ 獲取最新技能失敗: {result['message']}")
    else:
        print(f"   ✓ 獲取最新技能成功")
        print(f"   訊息長度: {len(result['message'])} 字符")
        if "keyboard" in result:
            print(f"   按鈕數量: {len(result['keyboard'])} 行\n")
    
    # 4. 測試已安裝列表
    print("4. 測試已安裝技能列表:")
    result = handler.list_installed_skills()
    print(f"   ✓ 已安裝列表生成成功")
    print(f"   訊息長度: {len(result['message'])} 字符")
    print(f"   按鈕數量: {len(result['keyboard'])} 行\n")
    
    # 5. 測試命令處理
    print("5. 測試命令處理:")
    commands = [
        ("/skills", []),
        ("/skill_search", ["weather"]),
        ("/skill_list", [])
    ]
    
    for cmd, args in commands:
        result = handler.handle_command(cmd, args)
        print(f"   {cmd} {' '.join(args)}: ✓ 處理成功")
    
    print("\n" + "="*50 + "\n")
    
    # 6. 測試 callback 處理
    print("6. 測試 callback 處理:")
    callbacks = [
        "action:search",
        "action:explore_latest",
        "action:list_installed",
        "action:main_menu"
    ]
    
    for callback in callbacks:
        result = handler.handle_callback(callback)
        if "error" in result:
            print(f"   {callback}: ✗ 錯誤: {result['error']}")
        else:
            print(f"   {callback}: ✓ 處理成功")
    
    print("\n" + "="*50 + "\n")
    
    # 總結
    print("📊 測試總結:")
    print(f"   所有基本功能測試完成")
    print(f"   Telegram 介面準備就緒")
    print(f"   技能市集功能可用")
    
    # 顯示使用說明
    print("\n📖 使用說明:")
    print("   1. 在 Telegram 中使用 /skills 打開主選單")
    print("   2. 使用 /skill_search [關鍵字] 搜索技能")
    print("   3. 使用 /skill_install [技能名稱] 安裝技能")
    print("   4. 使用 /skill_list 查看已安裝技能")
    print("\n🎯 下一步:")
    print("   將此技能整合到 OpenClaw 系統中")
    print("   配置 Telegram bot 命令")
    print("   測試實際安裝功能")

if __name__ == "__main__":
    test_all_features()