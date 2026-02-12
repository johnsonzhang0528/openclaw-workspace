"""
警報系統模組 - 負責閾值檢測、警報通知和警報管理
"""

import time
import threading
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json

# 相對導入改為絕對導入
try:
    # 嘗試作為套件導入
    from .config import config
    from .data_store import AlertData, data_store
    from .session_tracker import SessionTracker, SessionStatus
    from .resource_monitor import ResourceMonitor
except ImportError:
    # 如果作為獨立腳本運行，使用直接導入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from config import config
    from data_store import AlertData, data_store
    from session_tracker import SessionTracker, SessionStatus
    from resource_monitor import ResourceMonitor

class AlertLevel(Enum):
    """警報等級枚舉"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class AlertRule:
    """警報規則"""
    name: str
    condition: str  # 條件表達式
    level: AlertLevel
    message_template: str
    cooldown_seconds: int = 300  # 冷卻時間
    enabled: bool = True
    
    def evaluate(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        評估警報條件
        
        Args:
            context: 評估上下文
            
        Returns:
            (是否觸發, 警報訊息)
        """
        if not self.enabled:
            return False, None
        
        try:
            # 簡單的條件評估（可擴展為更複雜的邏輯）
            condition_met = False
            
            # 這裡可以實現更複雜的條件解析
            # 目前支持簡單的閾值檢查
            if ">" in self.condition:
                parts = self.condition.split(">")
                if len(parts) == 2:
                    key = parts[0].strip()
                    threshold = float(parts[1].strip())
                    value = context.get(key)
                    if isinstance(value, (int, float)):
                        condition_met = value > threshold
            
            elif "<" in self.condition:
                parts = self.condition.split("<")
                if len(parts) == 2:
                    key = parts[0].strip()
                    threshold = float(parts[1].strip())
                    value = context.get(key)
                    if isinstance(value, (int, float)):
                        condition_met = value < threshold
            
            elif "==" in self.condition:
                parts = self.condition.split("==")
                if len(parts) == 2:
                    key = parts[0].strip()
                    expected = parts[1].strip().strip('"\'')
                    value = context.get(key)
                    condition_met = str(value) == expected
            
            if condition_met:
                # 生成警報訊息
                message = self.message_template.format(**context)
                return True, message
            
            return False, None
            
        except Exception as e:
            print(f"評估警報規則失敗: {e}")
            return False, None

class AlertSystem:
    """警報系統"""
    
    def __init__(self, session_tracker: SessionTracker, resource_monitor: ResourceMonitor):
        """
        初始化警報系統
        
        Args:
            session_tracker: 會話追蹤器實例
            resource_monitor: 資源監控器實例
        """
        self.session_tracker = session_tracker
        self.resource_monitor = resource_monitor
        
        # 警報規則
        self.rules: List[AlertRule] = []
        self.alert_history: Dict[str, datetime] = {}  # 警報ID -> 最後觸發時間
        self.lock = threading.RLock()
        self.running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # 初始化預設規則
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化預設警報規則"""
        # 資源使用率規則
        self.rules.extend([
            AlertRule(
                name="cpu_warning",
                condition="cpu_percent>80",
                level=AlertLevel.WARNING,
                message_template="⚠️ CPU 使用率過高: {cpu_percent:.1f}% (閾值: 80%)",
                cooldown_seconds=300
            ),
            AlertRule(
                name="cpu_critical",
                condition="cpu_percent>95",
                level=AlertLevel.CRITICAL,
                message_template="🚨 CPU 使用率嚴重過高: {cpu_percent:.1f}% (閾值: 95%)",
                cooldown_seconds=60
            ),
            AlertRule(
                name="memory_warning",
                condition="memory_percent>85",
                level=AlertLevel.WARNING,
                message_template="⚠️ 記憶體使用率過高: {memory_percent:.1f}% (閾值: 85%)",
                cooldown_seconds=300
            ),
            AlertRule(
                name="memory_critical",
                condition="memory_percent>95",
                level=AlertLevel.CRITICAL,
                message_template="🚨 記憶體使用率嚴重過高: {memory_percent:.1f}% (閾值: 95%)",
                cooldown_seconds=60
            ),
            AlertRule(
                name="disk_warning",
                condition="disk_percent>90",
                level=AlertLevel.WARNING,
                message_template="⚠️ 磁碟使用率過高: {disk_percent:.1f}% (閾值: 90%)",
                cooldown_seconds=600
            ),
            AlertRule(
                name="disk_critical",
                condition="disk_percent>98",
                level=AlertLevel.CRITICAL,
                message_template="🚨 磁碟使用率嚴重過高: {disk_percent:.1f}% (閾值: 98%)",
                cooldown_seconds=300
            )
        ])
        
        # 會話相關規則
        self.rules.extend([
            AlertRule(
                name="too_many_sessions",
                condition="active_sessions>20",
                level=AlertLevel.WARNING,
                message_template="⚠️ 活動會話過多: {active_sessions} 個 (閾值: 20)",
                cooldown_seconds=600
            ),
            AlertRule(
                name="session_failed",
                condition="session_status=='failed'",
                level=AlertLevel.WARNING,
                message_template="⚠️ 會話失敗: {session_label}",
                cooldown_seconds=60
            ),
            AlertRule(
                name="session_stalled",
                condition="session_progress_stalled==True",
                level=AlertLevel.WARNING,
                message_template="⚠️ 會話停滯: {session_label} 已 {stalled_minutes} 分鐘無進展",
                cooldown_seconds=300
            )
        ])
    
    def start_monitoring(self, interval: int = None):
        """開始警報監控"""
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
        print(f"警報系統已啟動，監控間隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止警報監控"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("警報系統已停止")
    
    def _monitoring_loop(self, interval: int):
        """警報監控循環"""
        while self.running:
            try:
                self.check_alerts()
                time.sleep(interval)
            except Exception as e:
                print(f"警報監控錯誤: {e}")
                time.sleep(min(interval, 5))
    
    def check_alerts(self):
        """檢查所有警報規則"""
        try:
            # 收集監控數據
            context = self._collect_monitoring_context()
            
            # 檢查每個規則
            for rule in self.rules:
                triggered, message = rule.evaluate(context)
                
                if triggered:
                    # 檢查冷卻時間
                    alert_id = self._generate_alert_id(rule.name, context)
                    last_triggered = self.alert_history.get(alert_id)
                    
                    if last_triggered:
                        time_since_last = (datetime.now() - last_triggered).total_seconds()
                        if time_since_last < rule.cooldown_seconds:
                            continue  # 還在冷卻期
                    
                    # 觸發警報
                    self._trigger_alert(rule, message, context)
                    self.alert_history[alert_id] = datetime.now()
                    
        except Exception as e:
            print(f"檢查警報失敗: {e}")
    
    def _collect_monitoring_context(self) -> Dict[str, Any]:
        """收集監控上下文數據"""
        context = {}
        
        try:
            # 資源數據
            metrics = self.resource_monitor.get_current_metrics()
            if metrics:
                context.update({
                    'cpu_percent': metrics.cpu_percent,
                    'memory_percent': metrics.memory_percent,
                    'disk_percent': metrics.disk_percent,
                    'temperature': metrics.temperature,
                    'active_processes': metrics.active_processes
                })
            
            # 會話數據
            sessions = self.session_tracker.get_active_sessions()
            context['active_sessions'] = len(sessions)
            
            # 檢查停滯會話
            for session in sessions:
                # 檢查是否長時間無進展
                time_since_update = (datetime.now() - session.last_update).total_seconds() / 60
                if time_since_update > 10 and session.progress < 1.0:  # 10分鐘無進展
                    context.update({
                        'session_status': 'stalled',
                        'session_label': session.label,
                        'session_progress_stalled': True,
                        'stalled_minutes': int(time_since_update)
                    })
                    break
            
            # 系統時間
            context['timestamp'] = datetime.now().isoformat()
            context['hour'] = datetime.now().hour
            
        except Exception as e:
            print(f"收集監控上下文失敗: {e}")
        
        return context
    
    def _generate_alert_id(self, rule_name: str, context: Dict[str, Any]) -> str:
        """生成警報唯一ID"""
        # 使用規則名稱和關鍵上下文生成ID
        key_parts = [rule_name]
        
        # 添加相關上下文值
        for key in ['cpu_percent', 'memory_percent', 'disk_percent', 'active_sessions']:
            if key in context:
                key_parts.append(f"{key}:{context[key]}")
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    def _trigger_alert(self, rule: AlertRule, message: str, context: Dict[str, Any]):
        """觸發警報"""
        try:
            alert_id = self._generate_alert_id(rule.name, context)
            
            # 創建警報數據
            alert_data = AlertData(
                alert_id=alert_id,
                level=rule.level.value,
                message=message,
                timestamp=datetime.now(),
                acknowledged=False
            )
            
            # 保存到數據庫
            data_store.save_alert(alert_data)
            
            # 發送通知（這裡可以擴展為多種通知方式）
            self._send_notification(alert_data)
            
            print(f"警報觸發: {rule.level.value.upper()} - {message}")
            
        except Exception as e:
            print(f"觸發警報失敗: {e}")
    
    def _send_notification(self, alert: AlertData):
        """發送警報通知"""
        # 這裡可以實現多種通知方式：
        # 1. Telegram 通知
        # 2. 電子郵件通知
        # 3. Webhook 通知
        # 4. 系統通知
        
        # 目前先記錄到日誌，實際實現時需要根據配置發送
        notification_methods = []
        
        if config.alert.enable_email_alerts:
            notification_methods.append("email")
        
        if config.alert.enable_sms_alerts:
            notification_methods.append("sms")
        
        # 總是記錄到日誌
        print(f"警報通知 [{alert.level.upper()}]: {alert.message}")
        
        # TODO: 實現實際的通知發送邏輯
        # 例如：發送 Telegram 訊息、調用 Webhook 等
    
    def add_rule(self, rule: AlertRule):
        """添加警報規則"""
        with self.lock:
            self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """移除警報規則"""
        with self.lock:
            self.rules = [r for r in self.rules if r.name != rule_name]
    
    def enable_rule(self, rule_name: str, enabled: bool = True):
        """啟用或禁用警報規則"""
        with self.lock:
            for rule in self.rules:
                if rule.name == rule_name:
                    rule.enabled = enabled
                    break
    
    def get_active_alerts(self, level: Optional[str] = None) -> List[AlertData]:
        """獲取活動警報（未確認的）"""
        alerts = data_store.get_unacknowledged_alerts()
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """確認警報"""
        return data_store.acknowledge_alert(alert_id, acknowledged_by)
    
    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """獲取警報統計數據"""
        try:
            conn = data_store._get_connection()
            cursor = conn.cursor()
            
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # 各等級警報數量
            cursor.execute('''
                SELECT level, COUNT(*) 
                FROM alerts 
                WHERE timestamp >= ? 
                GROUP BY level
            ''', (cutoff,))
            
            level_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 已確認/未確認數量
            cursor.execute('''
                SELECT acknowledged, COUNT(*) 
                FROM alerts 
                WHERE timestamp >= ? 
                GROUP BY acknowledged
            ''', (cutoff,))
            
            ack_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'level_counts': level_counts,
                'acknowledged_counts': ack_counts,
                'time_range_hours': hours,
                'total_alerts': sum(level_counts.values())
            }
            
        except Exception as e:
            print(f"獲取警報統計失敗: {e}")
            return {}
    
    def manual_alert(self, level: str, message: str, source: str = "manual") -> bool:
        """手動觸發警報"""
        try:
            alert_id = hashlib.md5(f"{source}:{message}:{datetime.now().isoformat()}".encode()).hexdigest()[:16]
            
            alert_data = AlertData(
                alert_id=alert_id,
                level=level,
                message=f"[手動] {message}",
                timestamp=datetime.now(),
                acknowledged=False
            )
            
            data_store.save_alert(alert_data)
            self._send_notification(alert_data)
            
            return True
            
        except Exception as e:
            print(f"手動觸發警報失敗: {e}")
            return False

# 全局警報系統實例
alert_system = None  # 需要在初始化時創建

if __name__ == "__main__":
    print("測試警報系統...")
    
    # 創建模擬的追蹤器和監控器
    class MockSessionTracker:
        def get_active_sessions(self):
            return []
    
    class MockResourceMonitor:
        def get_current_metrics(self):
            class MockMetrics:
                cpu_percent = 90.5
                memory_percent = 85.2
                disk_percent = 92.1
                temperature = None
                active_processes = 50
            
            return MockMetrics()
    
    # 創建警報系統
    tracker = MockSessionTracker()
    monitor = MockResourceMonitor()
    system = AlertSystem(tracker, monitor)
    
    # 測試規則評估
    context = {
        'cpu_percent': 90.5,
        'memory_percent': 85.2,
        'disk_percent': 92.1,
        'active_sessions': 25
    }
    
    print("測試規則評估:")
    for rule in system.rules:
        triggered, message = rule.evaluate(context)
        if triggered:
            print(f"  {rule.name}: {message}")
    
    # 測試手動警報
    print("\n測試手動警報:")
    system.manual_alert("warning", "測試手動警報")
    
    print("\n測試完成！")