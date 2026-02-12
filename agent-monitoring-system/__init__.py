"""
Agent Monitoring System - OpenClaw 代理監控系統
"""

__version__ = "1.0.0"
__author__ = "OpenClaw Team"
__description__ = "Telegram 介面的即時可視化監控系統"

# 導出主要類別和函數
from .config import config, MonitoringConfig, DashboardConfig, AlertConfig, TelegramConfig, IntegrationConfig
from .data_store import data_store, SessionData, SessionStatus, ResourceData, AlertData
from .session_tracker import session_tracker, SessionTracker
from .resource_monitor import resource_monitor, ResourceMonitor, ResourceMetrics
from .telegram_dashboard import TelegramDashboard
from .alert_system import AlertSystem, AlertLevel, AlertRule
from .agent_monitor import AgentMonitor
from .integration import IntegrationManager, IssueTrackerIntegration, OpenClawSessionIntegration

# 方便導入的別名
__all__ = [
    # 配置
    'config',
    'MonitoringConfig',
    'DashboardConfig', 
    'AlertConfig',
    'TelegramConfig',
    'IntegrationConfig',
    
    # 數據存儲
    'data_store',
    'SessionData',
    'SessionStatus',
    'ResourceData',
    'AlertData',
    
    # 核心模組
    'session_tracker',
    'SessionTracker',
    'resource_monitor',
    'ResourceMonitor',
    'ResourceMetrics',
    
    # 功能模組
    'TelegramDashboard',
    'AlertSystem',
    'AlertLevel',
    'AlertRule',
    'AgentMonitor',
    
    # 整合模組
    'IntegrationManager',
    'IssueTrackerIntegration',
    'OpenClawSessionIntegration',
    
    # 元數據
    '__version__',
    '__author__',
    '__description__'
]

print(f"Agent Monitoring System v{__version__} 已載入")