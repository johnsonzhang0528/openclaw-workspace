#!/usr/bin/env python3
"""
Telegram 整合腳本
用於在 Telegram 中顯示監控儀表板
"""

import os
import sys
import json
from typing import Dict, List, Optional
from monitor_bot import SubagentMonitor

class TelegramMonitorBot:
    """Telegram 監控機器人"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """初始化機器人"""
        self.monitor = SubagentMonitor(config_path)
        self.config = self.monitor.config
        
    def generate_inline_keyboard(self, current_mode: str = "compact") -> List[List[Dict]]:
        """生成 inline keyboard"""
        buttons_config = self.config.get('telegram', {}).get('buttons', {})
        
        # 定義按鈕
        buttons = []
        
        # 第一行：顯示模式切換
        mode_buttons = []
        if current_mode != "compact":
            mode_buttons.append({
                "text": buttons_config.get("compact", "📊 精簡"),
                "callback_data": "monitor_compact"
            })
        if current_mode != "detailed":
            mode_buttons.append({
                "text": buttons_config.get("detailed", "📋 詳細"),
                "callback_data": "monitor_detailed"
            })
        if current_mode != "chart":
            mode_buttons.append({
                "text": buttons_config.get("chart", "📈 圖表"),
                "callback_data": "monitor_chart"
            })
        
        if mode_buttons:
            buttons.append(mode_buttons)
        
        # 第二行：控制按鈕
        control_buttons = [
            {
                "text": buttons_config.get("refresh", "🔄 刷新"),
                "callback_data": "monitor_refresh"
            },
            {
                "text": buttons_config.get("alerts", "🚨 警報"),
                "callback_data": "monitor_alerts"
            },
            {
                "text": buttons_config.get("history", "📜 歷史"),
                "callback_data": "monitor_history"
            }
        ]
        buttons.append(control_buttons)
        
        return buttons
    
    def generate_control_keyboard(self, task_id: str) -> List[List[Dict]]:
        """生成任務控制鍵盤"""
        buttons_config = self.config.get('telegram', {}).get('buttons', {})
        
        buttons = [
            [
                {
                    "text": buttons_config.get("pause", "⏸️  暫停"),
                    "callback_data": f"task_pause_{task_id}"
                },
                {
                    "text": buttons_config.get("resume", "▶️  繼續"),
                    "callback_data": f"task_resume_{task_id}"
                }
            ],
            [
                {
                    "text": buttons_config.get("stop", "⏹️  停止"),
                    "callback_data": f"task_stop_{task_id}"
                },
                {
                    "text": "🔙 返回",
                    "callback_data": "monitor_compact"
                }
            ]
        ]
        
        return buttons
    
    def generate_alert_message(self) -> str:
        """生成警報訊息"""
        # 這裡可以實現警報系統
        # 目前先返回簡單訊息
        return "🚨 警報系統\n目前沒有未處理的警報。"
    
    def generate_history_message(self) -> str:
        """生成歷史記錄訊息"""
        # 這裡可以實現歷史記錄查詢
        # 目前先返回簡單訊息
        return "📜 歷史記錄\n最近24小時內沒有任務記錄。"
    
    def handle_callback(self, callback_data: str) -> Dict:
        """處理回調數據"""
        result = {
            "text": "",
            "keyboard": None,
            "mode": "compact"
        }
        
        if callback_data.startswith("monitor_"):
            mode = callback_data.replace("monitor_", "")
            
            if mode == "refresh":
                # 刷新當前模式
                mode = "compact"
            elif mode == "alerts":
                result["text"] = self.generate_alert_message()
                result["keyboard"] = [[{"text": "🔙 返回", "callback_data": "monitor_compact"}]]
                return result
            elif mode == "history":
                result["text"] = self.generate_history_message()
                result["keyboard"] = [[{"text": "🔙 返回", "callback_data": "monitor_compact"}]]
                return result
            
            result["mode"] = mode
            result["text"] = self.monitor.generate_dashboard(mode)
            result["keyboard"] = self.generate_inline_keyboard(mode)
            
        elif callback_data.startswith("task_"):
            # 任務控制回調
            parts = callback_data.split("_")
            if len(parts) >= 3:
                action = parts[1]
                task_id = parts[2]
                
                # 這裡可以實現實際的任務控制邏輯
                if action == "pause":
                    result["text"] = f"⏸️  任務 {task_id[:8]}... 已暫停"
                elif action == "resume":
                    result["text"] = f"▶️  任務 {task_id[:8]}... 已繼續"
                elif action == "stop":
                    result["text"] = f"⏹️  任務 {task_id[:8]}... 已停止"
                
                result["keyboard"] = [[{"text": "🔙 返回", "callback_data": "monitor_compact"}]]
        
        return result
    
    def get_help_message(self) -> str:
        """獲取幫助訊息"""
        help_text = """
📚 監控儀表板幫助

基本命令：
/monitor - 顯示監控儀表板（精簡模式）
/monitor detail - 詳細模式
/monitor chart - 圖表模式
/monitor help - 顯示此幫助訊息

命令別名：
/dashboard, /status = /monitor
/detail, /full = /monitor detail
/charts, /graph = /monitor chart

按鈕功能：
📊 精簡 - 簡要顯示任務狀態
📋 詳細 - 顯示詳細任務資訊
📈 圖表 - 顯示資源使用趨勢
🔄 刷新 - 刷新當前顯示
🚨 警報 - 查看系統警報
📜 歷史 - 查看歷史記錄

任務控制：
⏸️  暫停 - 暫停選中任務
▶️  繼續 - 繼續暫停的任務
⏹️  停止 - 停止異常任務

資料更新：
• 任務狀態：即時更新
• 系統資源：每30秒更新
• 圖表資料：每5分鐘更新
        """
        return help_text.strip()

def main():
    """主函數 - 測試用"""
    bot = TelegramMonitorBot()
    
    # 測試不同模式
    print("測試精簡模式:")
    print(bot.monitor.generate_compact_dashboard())
    print("\n" + "="*50 + "\n")
    
    print("測試詳細模式:")
    print(bot.monitor.generate_detailed_dashboard())
    print("\n" + "="*50 + "\n")
    
    print("測試圖表模式:")
    print(bot.monitor.generate_chart_dashboard())
    print("\n" + "="*50 + "\n")
    
    print("測試幫助訊息:")
    print(bot.get_help_message())

if __name__ == "__main__":
    main()