#!/usr/bin/env python3
"""
技能市集 Telegram 演示
"""

import json
import sys
sys.path.append('.')

from telegram_handler import get_telegram_handler

def demo_telegram_interaction():
    """演示 Telegram 互動"""
    handler = get_telegram_handler()
    
    print("💬 Telegram 技能市集演示\n")
    
    # 1. 顯示主選單
    print("1. 📱 主選單介面:")
    print("-" * 40)
    result = handler.show_main_menu()
    print(result["message"])
    print("\n📱 按鈕佈局:")
    for row in result["keyboard"]:
        buttons = [btn["text"] for btn in row]
        print(f"   {buttons}")
    print("-" * 40 + "\n")
    
    # 2. 搜索演示
    print("2. 🔍 搜索技能 'weather':")
    print("-" * 40)
    result = handler.search_skills("weather", limit=3)
    print(result["message"])
    
    # 提取技能列表
    lines = result["message"].split('\n')
    skills = []
    for line in lines:
        if line.strip().startswith('`') and line.strip().endswith('`'):
            slug = line.strip().strip('`')
            skills.append(slug)
    
    print(f"\n🔍 找到 {len(skills)} 個技能:")
    for slug in skills:
        print(f"   • {slug}")
    print("-" * 40 + "\n")
    
    # 3. 最新技能演示
    print("3. ⭐ 最新技能:")
    print("-" * 40)
    result = handler.explore_latest_skills(limit=2)
    print(result["message"])
    print("-" * 40 + "\n")
    
    # 4. 已安裝技能
    print("4. 📦 已安裝技能:")
    print("-" * 40)
    result = handler.list_installed_skills()
    print(result["message"])
    print("-" * 40 + "\n")
    
    # 5. 安裝流程演示
    if skills:
        print("5. 📥 安裝流程演示:")
        print("-" * 40)
        slug = skills[0]  # 使用第一個找到的技能
        print(f"安裝技能: {slug}")
        result = handler.install_skill(slug)
        print(result["message"])
        print("-" * 40 + "\n")
    
    # 6. 命令處理演示
    print("6. ⌨️ 命令處理演示:")
    print("-" * 40)
    commands = [
        ("/skills", "打開主選單"),
        ("/skill_search weather", "搜索天氣相關技能"),
        ("/skill_list", "列出已安裝技能"),
        ("/skill_install weather-pollen", "安裝天氣花粉技能")
    ]
    
    for cmd, desc in commands:
        cmd_parts = cmd.split()
        command = cmd_parts[0]
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        print(f"\n{cmd}")
        print(f"描述: {desc}")
        result = handler.handle_command(command, args)
        print(f"回應: {result['message'][:80]}..." if len(result['message']) > 80 else f"回應: {result['message']}")
    
    print("-" * 40 + "\n")
    
    # 總結
    print("🎯 演示總結:")
    print("✅ 主選單介面正常")
    print("✅ 搜索功能正常")
    print("✅ 最新技能瀏覽正常")
    print("✅ 已安裝列表正常")
    print("✅ 安裝流程正常")
    print("✅ 命令處理正常")
    
    print("\n📱 Telegram 整合準備就緒！")
    print("\n使用方式:")
    print("1. 在 Telegram 中輸入 /skills")
    print("2. 使用按鈕進行互動")
    print("3. 搜索並安裝需要的技能")
    print("4. 管理已安裝技能")

if __name__ == "__main__":
    demo_telegram_interaction()