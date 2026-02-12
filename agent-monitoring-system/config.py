"""
Agent Monitoring System 配置管理
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

@dataclass
class TelegramConfig:
    """Telegram Bot 配置"""
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = True
    disable_notification: bool = False

@dataclass
class MonitoringConfig:
    """監控系統配置"""
    polling_interval: int = int(os.getenv("POLLING_INTERVAL", "30"))  # 秒
    history_retention_days: int = int(os.getenv("HISTORY_RETENTION_DAYS", "7"))
    max_sessions: int = int(os.getenv("MAX_SESSIONS", "50"))
    enable_resource_monitoring: bool = os.getenv("ENABLE_RESOURCE_MONITORING", "true").lower() == "true"
    enable_alerting: bool = os.getenv("ENABLE_ALERTING", "true").lower() == "true"
    
    # 資源閾值
    cpu_threshold: float = float(os.getenv("CPU_THRESHOLD", "80.0"))  # %
    memory_threshold: float = float(os.getenv("MEMORY_THRESHOLD", "85.0"))  # %
    disk_threshold: float = float(os.getenv("DISK_THRESHOLD", "90.0"))  # %

@dataclass
class OpenClawConfig:
    """OpenClaw 配置"""
    gateway_url: str = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:8080")
    api_key: str = os.getenv("OPENCLAW_API_KEY", "")
    timeout: int = int(os.getenv("OPENCLAW_TIMEOUT", "10"))

@dataclass
class DashboardConfig:
    """儀表板配置"""
    refresh_interval: int = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "60"))  # 秒
    max_history_points: int = int(os.getenv("MAX_HISTORY_POINTS", "100"))
    enable_charts: bool = os.getenv("ENABLE_CHARTS", "true").lower() == "true"
    compact_mode: bool = os.getenv("COMPACT_MODE", "false").lower() == "true"

@dataclass
class AlertConfig:
    """警報配置"""
    alert_cooldown: int = int(os.getenv("ALERT_COOLDOWN", "300"))  # 秒
    max_alerts_per_hour: int = int(os.getenv("MAX_ALERTS_PER_HOUR", "10"))
    enable_email_alerts: bool = os.getenv("ENABLE_EMAIL_ALERTS", "false").lower() == "true"
    enable_sms_alerts: bool = os.getenv("ENABLE_SMS_ALERTS", "false").lower() == "true"
    
    # 嚴重等級
    critical_threshold: int = int(os.getenv("CRITICAL_THRESHOLD", "95"))
    warning_threshold: int = int(os.getenv("WARNING_THRESHOLD", "80"))

@dataclass
class IntegrationConfig:
    """整合配置"""
    enable_issue_tracker: bool = os.getenv("INTEGRATION_ENABLE_ISSUE_TRACKER", "true").lower() == "true"
    enable_openclaw_sessions: bool = os.getenv("INTEGRATION_ENABLE_OPENCLAW_SESSIONS", "true").lower() == "true"

class Config:
    """全局配置類別"""
    
    def __init__(self):
        self.telegram = TelegramConfig()
        self.monitoring = MonitoringConfig()
        self.openclaw = OpenClawConfig()
        self.dashboard = DashboardConfig()
        self.alert = AlertConfig()
        self.integration = IntegrationConfig()
        
        # 驗證必要配置
        self._validate_config()
    
    def _validate_config(self):
        """驗證配置是否完整"""
        if not self.telegram.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN 未設定")
        if not self.telegram.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID 未設定")
        
        if self.monitoring.polling_interval < 5:
            print("警告: POLLING_INTERVAL 過小，建議至少 10 秒")
        
        if self.alert.critical_threshold <= self.alert.warning_threshold:
            print("警告: CRITICAL_THRESHOLD 應大於 WARNING_THRESHOLD")
    
    def to_dict(self) -> dict:
        """將配置轉換為字典"""
        return {
            "telegram": {
                "bot_token": self.telegram.bot_token[:10] + "..." if self.telegram.bot_token else "",
                "chat_id": self.telegram.chat_id,
                "parse_mode": self.telegram.parse_mode
            },
            "monitoring": {
                "polling_interval": self.monitoring.polling_interval,
                "history_retention_days": self.monitoring.history_retention_days,
                "enable_resource_monitoring": self.monitoring.enable_resource_monitoring
            },
            "openclaw": {
                "gateway_url": self.openclaw.gateway_url,
                "timeout": self.openclaw.timeout
            },
            "integration": {
                "enable_issue_tracker": self.integration.enable_issue_tracker,
                "enable_openclaw_sessions": self.integration.enable_openclaw_sessions
            }
        }
    
    def __str__(self) -> str:
        """字串表示"""
        config_dict = self.to_dict()
        lines = ["Agent Monitoring System 配置:"]
        for category, settings in config_dict.items():
            lines.append(f"\n{category.upper()}:")
            for key, value in settings.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

# 全局配置實例
config = Config()

if __name__ == "__main__":
    print(config)