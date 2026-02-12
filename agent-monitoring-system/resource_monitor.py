"""
資源監控模組 - 負責監控系統資源使用情況
"""

import time
import threading
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import platform
import os

from data_store import ResourceData, data_store
from config import config

@dataclass
class ResourceMetrics:
    """資源指標數據"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    active_processes: int
    load_average: Tuple[float, float, float]
    temperature: Optional[float] = None
    battery_percent: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'network_sent': self.network_sent,
            'network_recv': self.network_recv,
            'active_processes': self.active_processes,
            'load_average': self.load_average,
            'temperature': self.temperature,
            'battery_percent': self.battery_percent
        }

class ResourceMonitor:
    """資源監控器"""
    
    def __init__(self):
        self.metrics_history: List[ResourceMetrics] = []
        self.network_io_start = None
        self.network_sent_start = 0
        self.network_recv_start = 0
        self.lock = threading.RLock()
        self.running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.max_history = 1000
        
        # 初始化網絡監控
        self._init_network_monitoring()
    
    def _init_network_monitoring(self):
        """初始化網絡監控基準值"""
        try:
            net_io = psutil.net_io_counters()
            self.network_sent_start = net_io.bytes_sent
            self.network_recv_start = net_io.bytes_recv
            self.network_io_start = datetime.now()
        except Exception as e:
            print(f"初始化網絡監控失敗: {e}")
    
    def start_monitoring(self, interval: int = None):
        """開始資源監控"""
        if self.running:
            return
        
        if interval is None:
            interval = config.monitoring.polling_interval
        
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        print(f"資源監控器已啟動，監控間隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止資源監控"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("資源監控器已停止")
    
    def _monitoring_loop(self, interval: int):
        """監控循環"""
        while self.running:
            try:
                metrics = self.collect_metrics()
                self._process_metrics(metrics)
                time.sleep(interval)
            except Exception as e:
                print(f"資源監控錯誤: {e}")
                time.sleep(min(interval, 5))
    
    def collect_metrics(self) -> ResourceMetrics:
        """收集系統資源指標"""
        try:
            timestamp = datetime.now()
            
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 記憶體使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁碟使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 網絡 I/O
            net_io = psutil.net_io_counters()
            network_sent = net_io.bytes_sent
            network_recv = net_io.bytes_recv
            
            # 活躍進程數
            active_processes = len([p for p in psutil.process_iter(['status']) 
                                  if p.info['status'] == psutil.STATUS_RUNNING])
            
            # 系統負載
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0.0, 0.0, 0.0)
            
            # 溫度（如果可用）
            temperature = None
            try:
                if hasattr(psutil, 'sensors_temperatures'):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        # 取第一個溫度感測器的值
                        for name, entries in temps.items():
                            if entries:
                                temperature = entries[0].current
                                break
            except:
                pass
            
            # 電池（如果可用）
            battery_percent = None
            try:
                if hasattr(psutil, 'sensors_battery'):
                    battery = psutil.sensors_battery()
                    if battery:
                        battery_percent = battery.percent
            except:
                pass
            
            return ResourceMetrics(
                timestamp=timestamp,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_sent=network_sent,
                network_recv=network_recv,
                active_processes=active_processes,
                load_average=load_avg,
                temperature=temperature,
                battery_percent=battery_percent
            )
            
        except Exception as e:
            print(f"收集資源指標失敗: {e}")
            # 返回基本指標
            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_sent=0,
                network_recv=0,
                active_processes=0,
                load_average=(0.0, 0.0, 0.0)
            )
    
    def _process_metrics(self, metrics: ResourceMetrics):
        """處理收集到的指標"""
        with self.lock:
            # 添加到歷史記錄
            self.metrics_history.append(metrics)
            
            # 限制歷史記錄大小
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history:]
            
            # 計算網絡流量速率（每秒）
            network_sent_rate = 0
            network_recv_rate = 0
            
            if len(self.metrics_history) >= 2:
                prev_metrics = self.metrics_history[-2]
                time_diff = (metrics.timestamp - prev_metrics.timestamp).total_seconds()
                
                if time_diff > 0:
                    network_sent_rate = (metrics.network_sent - prev_metrics.network_sent) / time_diff
                    network_recv_rate = (metrics.network_recv - prev_metrics.network_recv) / time_diff
            
            # 保存到數據庫
            resource_data = ResourceData(
                timestamp=metrics.timestamp,
                cpu_percent=metrics.cpu_percent,
                memory_percent=metrics.memory_percent,
                disk_percent=metrics.disk_percent,
                network_sent=int(network_sent_rate),
                network_recv=int(network_recv_rate),
                active_sessions=0  # 這個需要從會話追蹤器獲取
            )
            
            data_store.save_resource_data(resource_data)
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """獲取當前資源指標"""
        with self.lock:
            if not self.metrics_history:
                return None
            return self.metrics_history[-1]
    
    def get_metrics_history(self, minutes: int = 60) -> List[ResourceMetrics]:
        """獲取指定時間內的指標歷史"""
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            return [
                metrics for metrics in self.metrics_history
                if metrics.timestamp >= cutoff
            ]
    
    def get_resource_stats(self, minutes: int = 5) -> Dict[str, Any]:
        """獲取資源統計數據"""
        history = self.get_metrics_history(minutes)
        
        if not history:
            return {}
        
        # 計算統計數據
        cpu_values = [m.cpu_percent for m in history]
        memory_values = [m.memory_percent for m in history]
        disk_values = [m.disk_percent for m in history]
        
        def safe_stats(values):
            if not values:
                return {'avg': 0, 'min': 0, 'max': 0}
            return {
                'avg': sum(values) / len(values),
                'min': min(values),
                'max': max(values)
            }
        
        stats = {
            'cpu': safe_stats(cpu_values),
            'memory': safe_stats(memory_values),
            'disk': safe_stats(disk_values),
            'samples': len(history),
            'time_range': {
                'start': history[0].timestamp.isoformat(),
                'end': history[-1].timestamp.isoformat()
            }
        }
        
        # 檢查是否超過閾值
        thresholds = {
            'cpu': config.monitoring.cpu_threshold,
            'memory': config.monitoring.memory_threshold,
            'disk': config.monitoring.disk_threshold
        }
        
        alerts = {}
        for resource, threshold in thresholds.items():
            current = history[-1].__dict__.get(f'{resource}_percent', 0)
            if current > threshold:
                alerts[resource] = {
                    'current': current,
                    'threshold': threshold,
                    'status': 'warning' if current < 90 else 'critical'
                }
        
        if alerts:
            stats['alerts'] = alerts
        
        return stats
    
    def get_system_info(self) -> Dict[str, Any]:
        """獲取系統信息"""
        try:
            info = {
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor()
                },
                'python': {
                    'version': platform.python_version(),
                    'implementation': platform.python_implementation()
                },
                'cpu': {
                    'physical_cores': psutil.cpu_count(logical=False),
                    'total_cores': psutil.cpu_count(logical=True),
                    'frequency': psutil.cpu_freq().current if hasattr(psutil.cpu_freq(), 'current') else None
                },
                'memory': {
                    'total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                    'available_gb': round(psutil.virtual_memory().available / (1024**3), 2)
                },
                'disk': {
                    'total_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
                    'free_gb': round(psutil.disk_usage('/').free / (1024**3), 2)
                },
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
            
            # 嘗試獲取更多信息
            try:
                info['hostname'] = platform.node()
            except:
                pass
            
            try:
                info['username'] = os.getlogin()
            except:
                pass
            
            return info
            
        except Exception as e:
            print(f"獲取系統信息失敗: {e}")
            return {'error': str(e)}
    
    def check_resource_health(self) -> Dict[str, str]:
        """檢查資源健康狀態"""
        metrics = self.get_current_metrics()
        if not metrics:
            return {'status': 'unknown', 'message': '無可用指標'}
        
        health_status = 'healthy'
        issues = []
        
        # 檢查 CPU
        if metrics.cpu_percent > config.monitoring.cpu_threshold:
            issues.append(f"CPU 使用率過高: {metrics.cpu_percent:.1f}%")
            if metrics.cpu_percent > 90:
                health_status = 'critical'
            else:
                health_status = 'warning'
        
        # 檢查記憶體
        if metrics.memory_percent > config.monitoring.memory_threshold:
            issues.append(f"記憶體使用率過高: {metrics.memory_percent:.1f}%")
            if metrics.memory_percent > 90:
                health_status = 'critical'
            else:
                health_status = 'warning'
        
        # 檢查磁碟
        if metrics.disk_percent > config.monitoring.disk_threshold:
            issues.append(f"磁碟使用率過高: {metrics.disk_percent:.1f}%")
            if metrics.disk_percent > 95:
                health_status = 'critical'
            else:
                health_status = 'warning'
        
        # 檢查溫度
        if metrics.temperature and metrics.temperature > 80:
            issues.append(f"系統溫度過高: {metrics.temperature:.1f}°C")
            health_status = 'warning'
        
        return {
            'status': health_status,
            'issues': issues,
            'timestamp': metrics.timestamp.isoformat()
        }

# 全局資源監控器實例
resource_monitor = ResourceMonitor()

if __name__ == "__main__":
    # 測試資源監控器
    monitor = ResourceMonitor()
    
    # 收集一次指標
    metrics = monitor.collect_metrics()
    print(f"收集到的指標: {metrics.to_dict()}")
    
    # 獲取系統信息
    system_info = monitor.get_system_info()
    print(f"系統信息: {system_info}")
    
    # 測試健康檢查
    health = monitor.check_resource_health()
    print(f"資源健康狀態: {health}")
    
    # 啟動監控（短時間測試）
    monitor.start_monitoring(interval=2)
    time.sleep(6)
    monitor.stop_monitoring()
    
    # 獲取歷史數據
    history = monitor.get_metrics_history(minutes=1)
    print(f"歷史數據點數: {len(history)}")
    
    # 獲取統計數據
    stats = monitor.get_resource_stats(minutes=1)
    print(f"資源統計: {stats}")