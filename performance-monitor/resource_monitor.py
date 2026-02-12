#!/usr/bin/env python3
"""
資源監控模組
監控系統資源使用情況：CPU、記憶體、磁碟、網路、進程等
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics
from collections import deque

from .config import Config
from .utils import format_bytes, format_percentage, format_timestamp

logger = logging.getLogger(__name__)

@dataclass
class ResourceMetrics:
    """資源指標數據類別"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_usage_percent: float
    disk_used: int
    disk_total: int
    network_sent: int
    network_recv: int
    network_sent_rate: float
    network_recv_rate: float
    process_count: int
    load_average: Tuple[float, float, float]
    swap_percent: float
    swap_used: int
    swap_total: int
    
@dataclass
class ProcessInfo:
    """進程資訊"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int
    status: str
    create_time: float
    cmdline: List[str]

class ResourceMonitor:
    """資源監控器"""
    
    def __init__(self, config: Config):
        """初始化資源監控器"""
        self.config = config
        self.running = False
        self.metrics_history = deque(maxlen=config.metrics_history_size)
        self.process_history = deque(maxlen=config.process_history_size)
        self.alerts = []
        self.last_network_stats = None
        self.last_network_time = None
        
    async def start(self):
        """啟動資源監控"""
        if self.running:
            logger.warning("資源監控已在運行中")
            return
            
        logger.info("啟動資源監控...")
        self.running = True
        
        # 初始化網路統計
        self.last_network_stats = psutil.net_io_counters()
        self.last_network_time = time.time()
        
        # 啟動監控任務
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
    async def stop(self):
        """停止資源監控"""
        if not self.running:
            return
            
        logger.info("停止資源監控...")
        self.running = False
        
        if hasattr(self, 'monitor_task'):
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
                
        logger.info("資源監控已停止")
        
    async def _monitor_loop(self):
        """監控循環"""
        while self.running:
            try:
                # 收集指標
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # 檢查警報
                await self._check_alerts(metrics)
                
                # 收集進程資訊
                processes = await self._collect_processes()
                self.process_history.append(processes)
                
                # 等待下一個收集間隔
                await asyncio.sleep(self.config.collection_interval)
                
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                await asyncio.sleep(1)
                
    async def _collect_metrics(self) -> ResourceMetrics:
        """收集系統指標"""
        timestamp = time.time()
        
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 記憶體使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = memory.used
        memory_total = memory.total
        
        # 磁碟使用率
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.percent
        disk_used = disk.used
        disk_total = disk.total
        
        # 網路統計
        current_network_stats = psutil.net_io_counters()
        current_time = time.time()
        
        network_sent = current_network_stats.bytes_sent
        network_recv = current_network_stats.bytes_recv
        
        # 計算網路速率
        if self.last_network_stats and self.last_network_time:
            time_diff = current_time - self.last_network_time
            if time_diff > 0:
                network_sent_rate = (current_network_stats.bytes_sent - self.last_network_stats.bytes_sent) / time_diff
                network_recv_rate = (current_network_stats.bytes_recv - self.last_network_stats.bytes_recv) / time_diff
            else:
                network_sent_rate = 0
                network_recv_rate = 0
        else:
            network_sent_rate = 0
            network_recv_rate = 0
            
        self.last_network_stats = current_network_stats
        self.last_network_time = current_time
        
        # 進程數量
        process_count = len(psutil.pids())
        
        # 系統負載
        try:
            load_avg = psutil.getloadavg()
        except:
            load_avg = (0, 0, 0)
            
        # 交換空間
        swap = psutil.swap_memory()
        swap_percent = swap.percent
        swap_used = swap.used
        swap_total = swap.total
        
        return ResourceMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used=memory_used,
            memory_total=memory_total,
            disk_usage_percent=disk_usage_percent,
            disk_used=disk_used,
            disk_total=disk_total,
            network_sent=network_sent,
            network_recv=network_recv,
            network_sent_rate=network_sent_rate,
            network_recv_rate=network_recv_rate,
            process_count=process_count,
            load_average=load_avg,
            swap_percent=swap_percent,
            swap_used=swap_used,
            swap_total=swap_total
        )
        
    async def _collect_processes(self) -> List[ProcessInfo]:
        """收集進程資訊"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'status', 'create_time', 'cmdline']):
            try:
                info = proc.info
                processes.append(ProcessInfo(
                    pid=info['pid'],
                    name=info['name'],
                    cpu_percent=info['cpu_percent'] or 0,
                    memory_percent=info['memory_percent'] or 0,
                    memory_rss=info['memory_info'].rss if info['memory_info'] else 0,
                    status=info['status'],
                    create_time=info['create_time'],
                    cmdline=info['cmdline'] or []
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # 按 CPU 使用率排序
        processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        
        return processes[:self.config.top_processes_limit]
        
    async def _check_alerts(self, metrics: ResourceMetrics):
        """檢查警報條件"""
        alerts = []
        
        # CPU 警報
        if metrics.cpu_percent > self.config.cpu_alert_threshold:
            alerts.append({
                "type": "cpu",
                "level": "warning",
                "message": f"CPU 使用率過高: {metrics.cpu_percent:.1f}%",
                "value": metrics.cpu_percent,
                "threshold": self.config.cpu_alert_threshold,
                "timestamp": metrics.timestamp
            })
            
        # 記憶體警報
        if metrics.memory_percent > self.config.memory_alert_threshold:
            alerts.append({
                "type": "memory",
                "level": "warning",
                "message": f"記憶體使用率過高: {metrics.memory_percent:.1f}%",
                "value": metrics.memory_percent,
                "threshold": self.config.memory_alert_threshold,
                "timestamp": metrics.timestamp
            })
            
        # 磁碟警報
        if metrics.disk_usage_percent > self.config.disk_alert_threshold:
            alerts.append({
                "type": "disk",
                "level": "warning",
                "message": f"磁碟使用率過高: {metrics.disk_usage_percent:.1f}%",
                "value": metrics.disk_usage_percent,
                "threshold": self.config.disk_alert_threshold,
                "timestamp": metrics.timestamp
            })
            
        # 添加新警報
        for alert in alerts:
            self.alerts.append(alert)
            
        # 限制警報數量
        if len(self.alerts) > self.config.max_alerts:
            self.alerts = self.alerts[-self.config.max_alerts:]
            
    async def get_current_metrics(self) -> Dict[str, Any]:
        """獲取當前指標"""
        if not self.metrics_history:
            return {}
            
        latest = self.metrics_history[-1]
        
        return {
            "cpu": {
                "percent": latest.cpu_percent,
                "load_average": latest.load_average
            },
            "memory": {
                "percent": latest.memory_percent,
                "used": latest.memory_used,
                "total": latest.memory_total,
                "used_formatted": format_bytes(latest.memory_used),
                "total_formatted": format_bytes(latest.memory_total)
            },
            "disk": {
                "percent": latest.disk_usage_percent,
                "used": latest.disk_used,
                "total": latest.disk_total,
                "used_formatted": format_bytes(latest.disk_used),
                "total_formatted": format_bytes(latest.disk_total)
            },
            "network": {
                "sent": latest.network_sent,
                "received": latest.network_recv,
                "sent_rate": latest.network_sent_rate,
                "received_rate": latest.network_recv_rate,
                "sent_formatted": format_bytes(latest.network_sent),
                "received_formatted": format_bytes(latest.network_recv),
                "sent_rate_formatted": f"{format_bytes(latest.network_sent_rate)}/s",
                "received_rate_formatted": f"{format_bytes(latest.network_recv_rate)}/s"
            },
            "system": {
                "process_count": latest.process_count,
                "swap_percent": latest.swap_percent,
                "swap_used": latest.swap_used,
                "swap_total": latest.swap_total,
                "swap_used_formatted": format_bytes(latest.swap_used),
                "swap_total_formatted": format_bytes(latest.swap_total)
            }
        }
        
    async def get_trends(self, hours: int = 1) -> Dict[str, Any]:
        """獲取趨勢數據"""
        if not self.metrics_history:
            return {}
            
        # 過濾指定時間範圍內的數據
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
            
        # 計算趨勢
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        disk_values = [m.disk_usage_percent for m in recent_metrics]
        
        return {
            "cpu": {
                "average": statistics.mean(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "min": min(cpu_values) if cpu_values else 0,
                "trend": "increasing" if len(cpu_values) > 1 and cpu_values[-1] > cpu_values[0] else "decreasing"
            },
            "memory": {
                "average": statistics.mean(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "min": min(memory_values) if memory_values else 0,
                "trend": "increasing" if len(memory_values) > 1 and memory_values[-1] > memory_values[0] else "decreasing"
            },
            "disk": {
                "average": statistics.mean(disk_values) if disk_values else 0,
                "max": max(disk_values) if disk_values else 0,
                "min": min(disk_values) if disk_values else 0,
                "trend": "increasing" if len(disk_values) > 1 and disk_values[-1] > disk_values[0] else "decreasing"
            }
        }
        
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """獲取活動警報"""
        # 過濾最近一小時的警報
        cutoff_time = time.time() - 3600
        recent_alerts = [a for a in self.alerts if a['timestamp'] >= cutoff_time]
        
        return recent_alerts
        
    async def get_top_processes(self, count: int = 10) -> List[Dict[str, Any]]:
        """獲取頂部進程"""
        if not self.process_history:
            return []
            
        latest_processes = self.process_history[-1]
        
        result = []
        for proc in latest_processes[:count]:
            result.append({
                "pid": proc.pid,
                "name": proc.name,
                "cpu_percent": proc.cpu_percent,
                "memory_percent": proc.memory_percent,
                "memory_rss": proc.memory_rss,
                "memory_rss_formatted": format_bytes(proc.memory_rss),
                "status": proc.status,
                "cmdline": " ".join(proc.cmdline) if proc.cmdline else proc.name
            })
            
        return result
        
    def get_status(self) -> Dict[str, Any]:
        """獲取監控器狀態"""
        return {
            "running": self.running,
            "metrics_count": len(self.metrics_history),
            "processes_count": len(self.process_history) if self.process_history else 0,
            "alerts_count": len(self.alerts),
            "config": self.config.get_summary()
        }