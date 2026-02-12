"""
任務監控規則設定檔
定義任務監控的規則、觸發條件和配置
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
from datetime import datetime, timedelta

class TaskStatus(Enum):
    """任務狀態枚舉"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 進行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失敗
    CANCELLED = "cancelled"  # 已取消
    PAUSED = "paused"        # 已暫停

class TaskPriority(Enum):
    """任務優先級枚舉"""
    LOW = "low"          # 低優先級
    NORMAL = "normal"    # 正常優先級
    HIGH = "high"        # 高優先級
    CRITICAL = "critical" # 關鍵優先級

class AlertType(Enum):
    """警報類型枚舉"""
    TASK_STARTED = "task_started"          # 任務開始
    TASK_COMPLETED = "task_completed"      # 任務完成
    TASK_FAILED = "task_failed"            # 任務失敗
    TASK_TIMEOUT = "task_timeout"          # 任務超時
    TASK_STALLED = "task_stalled"          # 任務停滯
    RESOURCE_EXCEEDED = "resource_exceeded" # 資源超限
    PROGRESS_SLOW = "progress_slow"        # 進度緩慢

@dataclass
class TaskMonitoringRule:
    """任務監控規則"""
    rule_id: str
    name: str
    description: str = ""
    
    # 觸發條件
    auto_start_monitoring: bool = True  # 任務開始時自動監控
    monitor_execution_time: bool = True  # 監控執行時間
    monitor_resource_usage: bool = True  # 監控資源使用
    monitor_progress_updates: bool = True  # 監控進度更新
    
    # 時間相關配置
    execution_timeout: Optional[int] = None  # 執行超時時間（秒）
    progress_check_interval: int = 30  # 進度檢查間隔（秒）
    stall_threshold: int = 300  # 停滯閾值（秒）
    
    # 資源閾值
    max_cpu_percent: float = 90.0  # 最大CPU使用率
    max_memory_mb: Optional[float] = None  # 最大記憶體使用（MB）
    max_disk_mb: Optional[float] = None  # 最大磁碟使用（MB）
    
    # 進度監控
    expected_progress_rate: Optional[float] = None  # 預期進度速率（%/秒）
    progress_stall_threshold: int = 60  # 進度停滯閾值（秒）
    
    # 警報配置
    enable_alerts: bool = True
    alert_on_start: bool = True
    alert_on_completion: bool = True
    alert_on_failure: bool = True
    alert_on_timeout: bool = True
    alert_on_stall: bool = True
    alert_on_resource_exceeded: bool = True
    
    # 通知目標
    notify_channels: List[str] = field(default_factory=lambda: ["telegram"])
    notify_users: List[str] = field(default_factory=list)
    
    # 自定義處理函數
    custom_handlers: Dict[str, Callable] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "auto_start_monitoring": self.auto_start_monitoring,
            "monitor_execution_time": self.monitor_execution_time,
            "monitor_resource_usage": self.monitor_resource_usage,
            "monitor_progress_updates": self.monitor_progress_updates,
            "execution_timeout": self.execution_timeout,
            "progress_check_interval": self.progress_check_interval,
            "stall_threshold": self.stall_threshold,
            "max_cpu_percent": self.max_cpu_percent,
            "max_memory_mb": self.max_memory_mb,
            "max_disk_mb": self.max_disk_mb,
            "expected_progress_rate": self.expected_progress_rate,
            "progress_stall_threshold": self.progress_stall_threshold,
            "enable_alerts": self.enable_alerts,
            "alert_on_start": self.alert_on_start,
            "alert_on_completion": self.alert_on_completion,
            "alert_on_failure": self.alert_on_failure,
            "alert_on_timeout": self.alert_on_timeout,
            "alert_on_stall": self.alert_on_stall,
            "alert_on_resource_exceeded": self.alert_on_resource_exceeded,
            "notify_channels": self.notify_channels,
            "notify_users": self.notify_users
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskMonitoringRule':
        """從字典創建規則"""
        return cls(**data)

@dataclass
class TaskProgressMetric:
    """任務進度指標"""
    task_id: str
    timestamp: datetime
    progress_percent: float  # 進度百分比 (0-100)
    status: TaskStatus
    message: str = ""
    
    # 資源使用
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    disk_mb: Optional[float] = None
    
    # 執行時間
    execution_time_seconds: float = 0.0
    
    # 自定義指標
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "progress_percent": self.progress_percent,
            "status": self.status.value,
            "message": self.message,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "execution_time_seconds": self.execution_time_seconds,
            "custom_metrics": self.custom_metrics
        }

class TaskMonitoringRulesManager:
    """任務監控規則管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化規則管理器"""
        self.config_path = config_path or "task_monitoring_rules.json"
        self.rules: Dict[str, TaskMonitoringRule] = {}
        self.default_rules: Dict[str, TaskMonitoringRule] = {}
        
        # 載入預設規則
        self._load_default_rules()
        
        # 載入自定義規則
        self.load_rules()
    
    def _load_default_rules(self):
        """載入預設規則"""
        # 預設監控規則
        default_rule = TaskMonitoringRule(
            rule_id="default",
            name="預設任務監控規則",
            description="適用於大多數任務的預設監控規則",
            auto_start_monitoring=True,
            monitor_execution_time=True,
            monitor_resource_usage=True,
            monitor_progress_updates=True,
            execution_timeout=3600,  # 1小時
            progress_check_interval=30,
            stall_threshold=300,
            max_cpu_percent=90.0,
            max_memory_mb=1024,  # 1GB
            max_disk_mb=100,  # 100MB
            enable_alerts=True,
            alert_on_start=True,
            alert_on_completion=True,
            alert_on_failure=True,
            alert_on_timeout=True,
            alert_on_stall=True,
            alert_on_resource_exceeded=True
        )
        
        # 快速任務規則
        quick_task_rule = TaskMonitoringRule(
            rule_id="quick_task",
            name="快速任務監控規則",
            description="適用於短時間任務的監控規則",
            auto_start_monitoring=True,
            monitor_execution_time=True,
            monitor_resource_usage=False,
            monitor_progress_updates=True,
            execution_timeout=300,  # 5分鐘
            progress_check_interval=10,
            stall_threshold=60,
            max_cpu_percent=95.0,
            enable_alerts=True,
            alert_on_start=False,
            alert_on_completion=True,
            alert_on_failure=True,
            alert_on_timeout=True,
            alert_on_stall=False,
            alert_on_resource_exceeded=False
        )
        
        # 資源密集型任務規則
        resource_intensive_rule = TaskMonitoringRule(
            rule_id="resource_intensive",
            name="資源密集型任務監控規則",
            description="適用於需要大量資源的任務",
            auto_start_monitoring=True,
            monitor_execution_time=True,
            monitor_resource_usage=True,
            monitor_progress_updates=True,
            execution_timeout=7200,  # 2小時
            progress_check_interval=60,
            stall_threshold=600,
            max_cpu_percent=80.0,
            max_memory_mb=4096,  # 4GB
            max_disk_mb=1024,  # 1GB
            enable_alerts=True,
            alert_on_start=True,
            alert_on_completion=True,
            alert_on_failure=True,
            alert_on_timeout=True,
            alert_on_stall=True,
            alert_on_resource_exceeded=True
        )
        
        # 背景任務規則
        background_task_rule = TaskMonitoringRule(
            rule_id="background_task",
            name="背景任務監控規則",
            description="適用於背景執行的任務",
            auto_start_monitoring=True,
            monitor_execution_time=True,
            monitor_resource_usage=True,
            monitor_progress_updates=False,
            execution_timeout=86400,  # 24小時
            progress_check_interval=300,
            stall_threshold=3600,
            max_cpu_percent=50.0,
            max_memory_mb=512,  # 512MB
            enable_alerts=True,
            alert_on_start=False,
            alert_on_completion=True,
            alert_on_failure=True,
            alert_on_timeout=True,
            alert_on_stall=False,
            alert_on_resource_exceeded=True
        )
        
        self.default_rules = {
            "default": default_rule,
            "quick_task": quick_task_rule,
            "resource_intensive": resource_intensive_rule,
            "background_task": background_task_rule
        }
    
    def load_rules(self):
        """從文件載入規則"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    rules_data = json.load(f)
                
                for rule_id, rule_data in rules_data.items():
                    self.rules[rule_id] = TaskMonitoringRule.from_dict(rule_data)
                
                print(f"已載入 {len(self.rules)} 個自定義監控規則")
            else:
                print("未找到自定義規則文件，使用預設規則")
                self.rules = self.default_rules.copy()
        except Exception as e:
            print(f"載入規則時發生錯誤: {e}")
            self.rules = self.default_rules.copy()
    
    def save_rules(self):
        """保存規則到文件"""
        try:
            rules_dict = {rule_id: rule.to_dict() for rule_id, rule in self.rules.items()}
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(rules_dict, f, indent=2, ensure_ascii=False)
            
            print(f"已保存 {len(self.rules)} 個監控規則到 {self.config_path}")
        except Exception as e:
            print(f"保存規則時發生錯誤: {e}")
    
    def get_rule(self, rule_id: str) -> Optional[TaskMonitoringRule]:
        """獲取指定規則"""
        # 先檢查自定義規則
        if rule_id in self.rules:
            return self.rules[rule_id]
        
        # 檢查預設規則
        if rule_id in self.default_rules:
            return self.default_rules[rule_id]
        
        return None
    
    def add_rule(self, rule: TaskMonitoringRule):
        """添加新規則"""
        self.rules[rule.rule_id] = rule
        print(f"已添加規則: {rule.name} ({rule.rule_id})")
    
    def update_rule(self, rule_id: str, rule: TaskMonitoringRule):
        """更新規則"""
        if rule_id in self.rules:
            self.rules[rule_id] = rule
            print(f"已更新規則: {rule.name} ({rule.rule_id})")
        else:
            print(f"規則不存在: {rule_id}")
    
    def delete_rule(self, rule_id: str):
        """刪除規則"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            print(f"已刪除規則: {rule_id}")
        else:
            print(f"規則不存在: {rule_id}")
    
    def list_rules(self) -> List[TaskMonitoringRule]:
        """列出所有規則"""
        return list(self.rules.values())
    
    def get_rule_for_task(self, task_type: str, task_priority: TaskPriority = TaskPriority.NORMAL) -> TaskMonitoringRule:
        """根據任務類型和優先級獲取合適的規則"""
        # 這裡可以實現更複雜的規則匹配邏輯
        if task_type == "quick":
            return self.get_rule("quick_task") or self.default_rules["quick_task"]
        elif task_type == "resource_intensive":
            return self.get_rule("resource_intensive") or self.default_rules["resource_intensive"]
        elif task_type == "background":
            return self.get_rule("background_task") or self.default_rules["background_task"]
        else:
            return self.get_rule("default") or self.default_rules["default"]

# 全局規則管理器實例
rules_manager = TaskMonitoringRulesManager()

if __name__ == "__main__":
    # 測試代碼
    manager = TaskMonitoringRulesManager()
    
    print("可用的監控規則:")
    for rule in manager.list_rules():
        print(f"- {rule.name} ({rule.rule_id}): {rule.description}")
    
    # 創建一個自定義規則
    custom_rule = TaskMonitoringRule(
        rule_id="custom_web_scraping",
        name="網頁爬蟲任務監控規則",
        description="專門用於網頁爬蟲任務的監控規則",
        execution_timeout=1800,  # 30分鐘
        progress_check_interval=15,
        max_memory_mb=2048,  # 2GB
        alert_on_start=False
    )
    
    manager.add_rule(custom_rule)
    manager.save_rules()