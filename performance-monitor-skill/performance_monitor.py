#!/usr/bin/env python3
"""
效能監控主程式
提供系統資源監控和報告功能
"""

import asyncio
import logging
import psutil
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import deque
import statistics

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """系統指標數據類別"""
    timestamp: float
    cpu_percent: float
    cpu_count: int
    memory_total: int
    memory_used: int
    memory_percent: float
    memory_available: int
    disk_total: int
    disk_used: int
    disk_percent: float
    network_sent: int
    network_recv: int
    load_avg_1: float
    load_avg_5: float
    load_avg_15: float
    process_count: int
    uptime: float

class PerformanceMonitor:
    """效能監控器"""
    
    def __init__(self, update_interval: int = 5, history_hours: int = 24):
        """初始化監控器"""
        self.update_interval = update_interval
        self.history_hours = history_hours
        self.running = False
        self.metrics_history = deque(maxlen=3600)  # 最多儲存1小時數據
        self.last_network_stats = None
        self.start_time = time.time()
        
    async def start(self):
        """啟動監控"""
        if self.running:
            logger.warning("監控器已在運行中")
            return
            
        logger.info(f"啟動效能監控器，更新間隔: {self.update_interval}秒")
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
    async def stop(self):
        """停止監控"""
        if not self.running:
            return
            
        logger.info("停止效能監控器")
        self.running = False
        if hasattr(self, 'monitor_task'):
            self.monitor_task.cancel()
            
    async def _monitor_loop(self):
        """監控循環"""
        while self.running:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                await asyncio.sleep(1)
                
    async def _collect_metrics(self) -> SystemMetrics:
        """收集系統指標"""
        timestamp = time.time()
        
        # CPU 資訊
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # 記憶體資訊
        memory = psutil.virtual_memory()
        
        # 磁碟資訊
        disk = psutil.disk_usage('/')
        
        # 網路資訊
        network = psutil.net_io_counters()
        network_sent = network.bytes_sent
        network_recv = network.bytes_recv
        
        # 計算網路速率
        sent_rate = 0
        recv_rate = 0
        if self.last_network_stats:
            time_diff = timestamp - self.last_network_stats['timestamp']
            if time_diff > 0:
                sent_rate = (network_sent - self.last_network_stats['sent']) / time_diff
                recv_rate = (network_recv - self.last_network_stats['recv']) / time_diff
                
        self.last_network_stats = {
            'timestamp': timestamp,
            'sent': network_sent,
            'recv': network_recv
        }
        
        # 系統負載
        load_avg = psutil.getloadavg()
        
        # 進程數量
        process_count = len(psutil.pids())
        
        # 系統運行時間
        uptime = time.time() - psutil.boot_time()
        
        return SystemMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            memory_total=memory.total,
            memory_used=memory.used,
            memory_percent=memory.percent,
            memory_available=memory.available,
            disk_total=disk.total,
            disk_used=disk.used,
            disk_percent=disk.percent,
            network_sent=network_sent,
            network_recv=network_recv,
            load_avg_1=load_avg[0],
            load_avg_5=load_avg[1],
            load_avg_15=load_avg[2],
            process_count=process_count,
            uptime=uptime
        )
        
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """獲取當前指標"""
        if not self.metrics_history:
            return None
        return self.metrics_history[-1]
        
    def get_history(self, minutes: int = 60) -> List[SystemMetrics]:
        """獲取歷史數據"""
        cutoff = time.time() - (minutes * 60)
        return [m for m in self.metrics_history if m.timestamp >= cutoff]
        
    def get_statistics(self, minutes: int = 15) -> Dict[str, Any]:
        """獲取統計數據"""
        history = self.get_history(minutes)
        if not history:
            return {}
            
        cpu_values = [m.cpu_percent for m in history]
        memory_values = [m.memory_percent for m in history]
        load_values = [m.load_avg_1 for m in history]
        
        return {
            'cpu': {
                'avg': statistics.mean(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'current': history[-1].cpu_percent
            },
            'memory': {
                'avg': statistics.mean(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'current': history[-1].memory_percent
            },
            'load': {
                'avg': statistics.mean(load_values),
                'max': max(load_values),
                'min': min(load_values),
                'current': history[-1].load_avg_1
            },
            'sample_count': len(history)
        }
        
    def format_metrics(self, metrics: SystemMetrics) -> str:
        """格式化指標為可讀字符串"""
        if not metrics:
            return "無可用數據"
            
        def format_bytes(bytes_num):
            """格式化字節數"""
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_num < 1024:
                    return f"{bytes_num:.1f} {unit}"
                bytes_num /= 1024
            return f"{bytes_num:.1f} PB"
            
        lines = []
        lines.append("📊 **系統效能報告**")
        lines.append(f"⏰ 時間: {datetime.fromtimestamp(metrics.timestamp).strftime('%H:%M:%S')}")
        lines.append("")
        
        # CPU
        lines.append(f"⚡ **CPU**: {metrics.cpu_percent:.1f}% ({metrics.cpu_count}核心)")
        
        # 記憶體
        mem_used_gb = metrics.memory_used / (1024**3)
        mem_total_gb = metrics.memory_total / (1024**3)
        lines.append(f"🧠 **記憶體**: {metrics.memory_percent:.1f}% ({mem_used_gb:.1f}/{mem_total_gb:.1f} GB)")
        
        # 磁碟
        disk_used_gb = metrics.disk_used / (1024**3)
        disk_total_gb = metrics.disk_total / (1024**3)
        lines.append(f"💾 **磁碟**: {metrics.disk_percent:.1f}% ({disk_used_gb:.1f}/{disk_total_gb:.1f} GB)")
        
        # 系統負載
        lines.append(f"📈 **系統負載**: {metrics.load_avg_1:.2f} ({metrics.load_avg_5:.2f}/{metrics.load_avg_15:.2f})")
        
        # 進程
        lines.append(f"🔢 **進程數**: {metrics.process_count}")
        
        # 運行時間
        uptime_hours = metrics.uptime / 3600
        lines.append(f"⏱️  **運行時間**: {uptime_hours:.1f} 小時")
        
        return "\n".join(lines)
        
    def get_top_processes(self, count: int = 5) -> List[Dict[str, Any]]:
        """獲取資源消耗最多的進程"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                if info['cpu_percent'] is not None and info['memory_percent'] is not None:
                    processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # 按 CPU 使用率排序
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return processes[:count]

# 全局監控器實例
_monitor_instance = None

def get_monitor() -> PerformanceMonitor:
    """獲取監控器實例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    return _monitor_instance

async def main():
    """主函數"""
    monitor = get_monitor()
    await monitor.start()
    
    try:
        # 運行10秒後顯示報告
        await asyncio.sleep(10)
        
        metrics = monitor.get_current_metrics()
        if metrics:
            print(monitor.format_metrics(metrics))
            
        # 顯示統計數據
        stats = monitor.get_statistics(5)
        if stats:
            print("\n📈 **5分鐘統計**:")
            print(f"CPU: 平均 {stats['cpu']['avg']:.1f}%, 最高 {stats['cpu']['max']:.1f}%")
            print(f"記憶體: 平均 {stats['memory']['avg']:.1f}%, 最高 {stats['memory']['max']:.1f}%")
            
        # 顯示熱門進程
        print("\n🔥 **資源消耗最多的進程**:")
        top_procs = monitor.get_top_processes(3)
        for i, proc in enumerate(top_procs, 1):
            print(f"{i}. {proc['name']}: CPU {proc['cpu_percent']:.1f}%, 記憶體 {proc['memory_percent']:.1f}%")
            
    finally:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())