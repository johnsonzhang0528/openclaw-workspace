#!/usr/bin/env python3
"""
Telegram 處理器
提供 Telegram 命令介面
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .performance_monitor import get_monitor, PerformanceMonitor

logger = logging.getLogger(__name__)

class TelegramPerformanceHandler:
    """Telegram 效能處理器"""
    
    def __init__(self):
        self.monitor = get_monitor()
        
    async def handle_command(self, command: str, args: list = None) -> str:
        """處理命令"""
        if args is None:
            args = []
            
        command = command.lower().strip()
        
        if command == "performance" or command == "perf":
            return await self.handle_performance(args)
        elif command == "help":
            return self.get_help()
        else:
            return "❓ 未知命令。使用 /performance help 查看可用命令。"
            
    async def handle_performance(self, args: list) -> str:
        """處理效能命令"""
        if not args:
            return await self.show_current_performance()
            
        subcommand = args[0].lower()
        
        if subcommand == "current" or subcommand == "now":
            return await self.show_current_performance()
        elif subcommand == "history" or subcommand == "trend":
            return await self.show_history()
        elif subcommand == "top" or subcommand == "processes":
            return await self.show_top_processes()
        elif subcommand == "stats" or subcommand == "statistics":
            return await self.show_statistics()
        elif subcommand == "help":
            return self.get_help()
        else:
            return f"❓ 未知子命令: {subcommand}\n{self.get_help()}"
            
    async def show_current_performance(self) -> str:
        """顯示當前效能"""
        try:
            # 確保監控器運行
            if not self.monitor.running:
                await self.monitor.start()
                await asyncio.sleep(1)  # 等待數據收集
                
            metrics = self.monitor.get_current_metrics()
            if not metrics:
                return "⏳ 正在收集數據，請稍候..."
                
            return self.monitor.format_metrics(metrics)
            
        except Exception as e:
            logger.error(f"顯示當前效能錯誤: {e}")
            return f"❌ 錯誤: {str(e)}"
            
    async def show_history(self) -> str:
        """顯示歷史趨勢"""
        try:
            stats = self.monitor.get_statistics(60)  # 60分鐘統計
            if not stats:
                return "📊 歷史數據不足，請稍候..."
                
            lines = []
            lines.append("📈 **60分鐘效能趨勢**")
            lines.append("")
            
            # CPU 趨勢
            cpu = stats['cpu']
            lines.append(f"⚡ **CPU 使用率**:")
            lines.append(f"  當前: {cpu['current']:.1f}%")
            lines.append(f"  平均: {cpu['avg']:.1f}%")
            lines.append(f"  最高: {cpu['max']:.1f}%")
            lines.append(f"  最低: {cpu['min']:.1f}%")
            lines.append("")
            
            # 記憶體趨勢
            memory = stats['memory']
            lines.append(f"🧠 **記憶體使用率**:")
            lines.append(f"  當前: {memory['current']:.1f}%")
            lines.append(f"  平均: {memory['avg']:.1f}%")
            lines.append(f"  最高: {memory['max']:.1f}%")
            lines.append(f"  最低: {memory['min']:.1f}%")
            lines.append("")
            
            # 系統負載
            load = stats['load']
            lines.append(f"📊 **系統負載 (1分鐘)**:")
            lines.append(f"  當前: {load['current']:.2f}")
            lines.append(f"  平均: {load['avg']:.2f}")
            lines.append(f"  最高: {load['max']:.2f}")
            lines.append(f"  最低: {load['min']:.2f}")
            lines.append("")
            
            lines.append(f"📋 數據樣本: {stats['sample_count']} 個")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"顯示歷史趨勢錯誤: {e}")
            return f"❌ 錯誤: {str(e)}"
            
    async def show_top_processes(self) -> str:
        """顯示熱門進程"""
        try:
            top_procs = self.monitor.get_top_processes(8)
            if not top_procs:
                return "🔍 未找到進程資訊"
                
            lines = []
            lines.append("🔥 **資源消耗最多的進程**")
            lines.append("")
            
            for i, proc in enumerate(top_procs, 1):
                name = proc['name'][:30]  # 限制名稱長度
                cpu = proc['cpu_percent']
                memory = proc['memory_percent']
                pid = proc['pid']
                
                # 根據 CPU 使用率添加表情符號
                if cpu > 50:
                    icon = "🔥"
                elif cpu > 20:
                    icon = "⚡"
                elif cpu > 5:
                    icon = "📈"
                else:
                    icon = "📊"
                    
                lines.append(f"{icon} **{i}. {name}** (PID: {pid})")
                lines.append(f"   CPU: {cpu:.1f}% | 記憶體: {memory:.1f}%")
                
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"顯示熱門進程錯誤: {e}")
            return f"❌ 錯誤: {str(e)}"
            
    async def show_statistics(self) -> str:
        """顯示詳細統計"""
        try:
            metrics = self.monitor.get_current_metrics()
            if not metrics:
                return "⏳ 正在收集數據，請稍候..."
                
            lines = []
            lines.append("📊 **詳細系統統計**")
            lines.append("")
            
            # 系統資訊
            lines.append(f"🖥️  **系統資訊**:")
            lines.append(f"  CPU 核心數: {metrics.cpu_count}")
            lines.append(f"  總記憶體: {metrics.memory_total / (1024**3):.1f} GB")
            lines.append(f"  總磁碟空間: {metrics.disk_total / (1024**3):.1f} GB")
            lines.append("")
            
            # 使用率
            lines.append(f"📈 **使用率分析**:")
            
            # CPU 狀態
            cpu_status = "🟢 正常"
            if metrics.cpu_percent > 90:
                cpu_status = "🔴 過高"
            elif metrics.cpu_percent > 70:
                cpu_status = "🟡 偏高"
            lines.append(f"  CPU: {metrics.cpu_percent:.1f}% {cpu_status}")
            
            # 記憶體狀態
            mem_status = "🟢 正常"
            if metrics.memory_percent > 90:
                mem_status = "🔴 過高"
            elif metrics.memory_percent > 80:
                mem_status = "🟡 偏高"
            lines.append(f"  記憶體: {metrics.memory_percent:.1f}% {mem_status}")
            
            # 磁碟狀態
            disk_status = "🟢 正常"
            if metrics.disk_percent > 95:
                disk_status = "🔴 過高"
            elif metrics.disk_percent > 85:
                disk_status = "🟡 偏高"
            lines.append(f"  磁碟: {metrics.disk_percent:.1f}% {disk_status}")
            lines.append("")
            
            # 負載分析
            lines.append(f"⚖️  **負載分析**:")
            load_per_core = metrics.load_avg_1 / metrics.cpu_count
            load_status = "🟢 正常"
            if load_per_core > 2:
                load_status = "🔴 過載"
            elif load_per_core > 1:
                load_status = "🟡 偏高"
            lines.append(f"  每核心負載: {load_per_core:.2f} {load_status}")
            lines.append(f"  建議: {'需要擴容' if load_per_core > 1.5 else '運行良好'}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"顯示詳細統計錯誤: {e}")
            return f"❌ 錯誤: {str(e)}"
            
    def get_help(self) -> str:
        """獲取幫助訊息"""
        lines = []
        lines.append("🤖 **效能監控幫助**")
        lines.append("")
        lines.append("**可用命令:**")
        lines.append("`/performance` - 顯示當前效能")
        lines.append("`/performance current` - 顯示當前效能")
        lines.append("`/performance history` - 顯示歷史趨勢")
        lines.append("`/performance top` - 顯示熱門進程")
        lines.append("`/performance stats` - 顯示詳細統計")
        lines.append("`/performance help` - 顯示此幫助")
        lines.append("")
        lines.append("**快捷命令:**")
        lines.append("`/perf` - `/performance` 的別名")
        lines.append("")
        lines.append("**數據更新:** 每5秒自動更新")
        
        return "\n".join(lines)
        
    def get_inline_buttons(self) -> list:
        """獲取 inline 按鈕"""
        return [
            [
                {"text": "📊 即時效能", "callback_data": "perf_current"},
                {"text": "📈 歷史趨勢", "callback_data": "perf_history"}
            ],
            [
                {"text": "🔥 熱門進程", "callback_data": "perf_top"},
                {"text": "📋 詳細統計", "callback_data": "perf_stats"}
            ],
            [
                {"text": "🔄 刷新", "callback_data": "perf_refresh"},
                {"text": "❓ 幫助", "callback_data": "perf_help"}
            ]
        ]

# 全局處理器實例
_handler_instance = None

def get_handler() -> TelegramPerformanceHandler:
    """獲取處理器實例"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = TelegramPerformanceHandler()
    return _handler_instance

async def test_handler():
    """測試處理器"""
    handler = get_handler()
    
    # 測試各個命令
    commands = [
        ("performance", []),
        ("performance", ["history"]),
        ("performance", ["top"]),
        ("performance", ["stats"]),
        ("help", [])
    ]
    
    for cmd, args in commands:
        print(f"\n{'='*50}")
        print(f"測試命令: {cmd} {args}")
        print(f"{'='*50}")
        result = await handler.handle_command(cmd, args)
        print(result)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_handler())