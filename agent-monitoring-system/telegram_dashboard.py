"""
Telegram 儀表板生成器 - 創建 HTML 格式的 Telegram 訊息
包含進度條視覺化、資源使用圖表、會話狀態顯示
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import math

# 相對導入改為絕對導入
try:
    # 嘗試作為套件導入
    from .config import config
    from .data_store import SessionData, SessionStatus
    from .session_tracker import SessionTracker
    from .resource_monitor import ResourceMonitor, ResourceMetrics
except ImportError:
    # 如果作為獨立腳本運行，使用直接導入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from config import config
    from data_store import SessionData, SessionStatus
    from session_tracker import SessionTracker
    from resource_monitor import ResourceMonitor, ResourceMetrics


class TelegramDashboard:
    """Telegram 儀表板生成器"""
    
    def __init__(self, session_tracker: SessionTracker, resource_monitor: ResourceMonitor):
        """
        初始化儀表板生成器
        
        Args:
            session_tracker: 會話追蹤器實例
            resource_monitor: 資源監控器實例
        """
        self.session_tracker = session_tracker
        self.resource_monitor = resource_monitor
        self.last_update = datetime.now()
        
        # 顏色定義
        self.colors = {
            "primary": "#3498db",
            "success": "#2ecc71",
            "warning": "#f39c12",
            "danger": "#e74c3c",
            "info": "#17a2b8",
            "dark": "#343a40",
            "light": "#f8f9fa",
            "secondary": "#6c757d"
        }
        
        # 狀態圖標
        self.status_icons = {
            SessionStatus.ACTIVE: "🟢",
            SessionStatus.COMPLETED: "✅",
            SessionStatus.FAILED: "❌",
            SessionStatus.PAUSED: "⏸️",
            SessionStatus.QUEUED: "⏳"
        }
    
    def generate_progress_bar(self, progress: float, width: int = 20) -> str:
        """
        生成進度條
        
        Args:
            progress: 進度 (0.0 到 1.0)
            width: 進度條寬度
            
        Returns:
            進度條字串
        """
        filled = int(progress * width)
        empty = width - filled
        
        # 根據進度選擇顏色
        if progress >= 0.8:
            color = self.colors["success"]
        elif progress >= 0.5:
            color = self.colors["warning"]
        else:
            color = self.colors["danger"]
        
        # 創建 HTML 進度條
        bar = f'<b>[</b>{"█" * filled}{"░" * empty}<b>]</b> {progress*100:.1f}%'
        return bar
    
    def generate_resource_gauge(self, value: float, max_value: float = 100.0, label: str = "") -> str:
        """
        生成資源使用量儀表
        
        Args:
            value: 當前值
            max_value: 最大值
            label: 標籤
            
        Returns:
            儀表字串
        """
        percentage = (value / max_value) * 100
        
        # 選擇圖標和顏色
        if percentage >= 90:
            icon = "🔴"
            color = self.colors["danger"]
        elif percentage >= 70:
            icon = "🟡"
            color = self.colors["warning"]
        else:
            icon = "🟢"
            color = self.colors["success"]
        
        # 創建簡單的儀表
        gauge = f'{icon} <b>{label}:</b> {value:.1f}/{max_value:.0f} ({percentage:.1f}%)'
        return gauge
    
    def generate_session_card(self, session: SessionData) -> str:
        """
        生成會話卡片
        
        Args:
            session: 會話數據
            
        Returns:
            會話卡片 HTML
        """
        icon = self.status_icons.get(session.status, "❓")
        status_text = session.status.value.upper()
        
        # 計算運行時間
        runtime = datetime.now() - session.start_time
        hours, remainder = divmod(runtime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # 生成進度條
        progress_bar = self.generate_progress_bar(session.progress)
        
        # 構建卡片
        card = f"""
{icon} <b>{session.label}</b> [{session.session_id[:8]}]
├─ 📊 <b>狀態:</b> {status_text}
├─ ⏱️ <b>運行時間:</b> {hours:02d}:{minutes:02d}:{seconds:02d}
├─ 🎯 <b>進度:</b> {progress_bar}
"""
        
        # 添加預計完成時間
        if session.estimated_completion:
            time_left = session.estimated_completion - datetime.now()
            if time_left.total_seconds() > 0:
                hours_left = int(time_left.total_seconds() // 3600)
                minutes_left = int((time_left.total_seconds() % 3600) // 60)
                card += f"└─ ⏳ <b>預計完成:</b> {hours_left}小時{minutes_left}分鐘後\n"
        
        return card
    
    def generate_resource_section(self) -> str:
        """
        生成資源使用情況區塊
        
        Returns:
            資源區塊 HTML
        """
        try:
            metrics = self.resource_monitor.get_current_metrics()
            
            section = "<b>📈 系統資源監控</b>\n"
            section += "─" * 30 + "\n"
            
            # CPU 使用率
            cpu_gauge = self.generate_resource_gauge(
                metrics.cpu_percent, 
                100.0, 
                "CPU"
            )
            section += f"{cpu_gauge}\n"
            
            # 記憶體使用率
            memory_gauge = self.generate_resource_gauge(
                metrics.memory_percent,
                100.0,
                "記憶體"
            )
            section += f"{memory_gauge}\n"
            
            # 磁碟使用率
            disk_gauge = self.generate_resource_gauge(
                metrics.disk_percent,
                100.0,
                "磁碟"
            )
            section += f"{disk_gauge}\n"
            
            # 網路流量
            if hasattr(metrics, 'network_sent_mb') and hasattr(metrics, 'network_recv_mb'):
                section += f"🌐 <b>網路:</b> ↑{metrics.network_sent_mb:.1f}MB ↓{metrics.network_recv_mb:.1f}MB\n"
            
            # 系統負載
            if hasattr(metrics, 'load_avg_1m'):
                section += f"⚖️ <b>系統負載:</b> {metrics.load_avg_1m:.2f} (1m)\n"
            
            return section
            
        except Exception as e:
            return f"<b>⚠️ 資源監控錯誤:</b> {str(e)}\n"
    
    def generate_sessions_section(self, limit: int = 10) -> str:
        """
        生成會話列表區塊
        
        Args:
            limit: 顯示的會話數量限制
            
        Returns:
            會話區塊 HTML
        """
        try:
            sessions = self.session_tracker.get_active_sessions(limit=limit)
            total_sessions = self.session_tracker.get_session_count()
            
            section = f"<b>🤖 活動會話 ({len(sessions)}/{total_sessions})</b>\n"
            section += "─" * 30 + "\n"
            
            if not sessions:
                section += "📭 目前沒有活動會話\n"
            else:
                for i, session in enumerate(sessions, 1):
                    card = self.generate_session_card(session)
                    section += card
                    if i < len(sessions):
                        section += "\n"
            
            return section
            
        except Exception as e:
            return f"<b>⚠️ 會話監控錯誤:</b> {str(e)}\n"
    
    def generate_alerts_section(self, alerts: List[Dict[str, Any]]) -> str:
        """
        生成警報區塊
        
        Args:
            alerts: 警報列表
            
        Returns:
            警報區塊 HTML
        """
        if not alerts:
            return ""
        
        section = "<b>🚨 系統警報</b>\n"
        section += "─" * 30 + "\n"
        
        for alert in alerts[:5]:  # 最多顯示5個警報
            timestamp = alert.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            time_str = timestamp.strftime("%H:%M:%S")
            severity = alert.get('severity', 'info')
            message = alert.get('message', '')
            
            # 根據嚴重等級選擇圖標
            if severity == 'critical':
                icon = "🔴"
            elif severity == 'warning':
                icon = "🟡"
            else:
                icon = "🔵"
            
            section += f"{icon} <b>[{time_str}]</b> {message}\n"
        
        if len(alerts) > 5:
            section += f"... 還有 {len(alerts) - 5} 個警報未顯示\n"
        
        return section
    
    def generate_statistics_section(self) -> str:
        """
        生成統計數據區塊
        
        Returns:
            統計區塊 HTML
        """
        try:
            stats = self.session_tracker.get_statistics()
            
            section = "<b>📊 系統統計</b>\n"
            section += "─" * 30 + "\n"
            
            # 會話統計
            section += f"📅 <b>今日會話:</b> {stats.get('today_sessions', 0)}\n"
            section += f"✅ <b>完成會話:</b> {stats.get('completed_sessions', 0)}\n"
            section += f"❌ <b>失敗會話:</b> {stats.get('failed_sessions', 0)}\n"
            section += f"⏱️ <b>平均運行時間:</b> {stats.get('avg_runtime_minutes', 0):.1f}分鐘\n"
            
            # 成功率
            success_rate = stats.get('success_rate', 0)
            section += f"🎯 <b>成功率:</b> {success_rate:.1f}%\n"
            
            return section
            
        except Exception as e:
            return f"<b>⚠️ 統計數據錯誤:</b> {str(e)}\n"
    
    def generate_full_dashboard(self, alerts: List[Dict[str, Any]] = None) -> str:
        """
        生成完整儀表板
        
        Args:
            alerts: 警報列表
            
        Returns:
            完整儀表板 HTML
        """
        if alerts is None:
            alerts = []
        
        # 更新時間
        self.last_update = datetime.now()
        update_time = self.last_update.strftime("%Y-%m-%d %H:%M:%S")
        
        # 構建儀表板
        dashboard = f"""
<b>🤖 OpenClaw Agent 監控儀表板</b>
<code>最後更新: {update_time}</code>
{"=" * 35}
"""
        
        # 添加警報區塊（如果有警報）
        alerts_section = self.generate_alerts_section(alerts)
        if alerts_section:
            dashboard += alerts_section + "\n"
        
        # 添加資源區塊
        dashboard += self.generate_resource_section() + "\n"
        
        # 添加會話區塊
        dashboard += self.generate_sessions_section() + "\n"
        
        # 添加統計區塊
        dashboard += self.generate_statistics_section()
        
        # 添加底部資訊
        dashboard += f"""
{"=" * 35}
<code>系統狀態: 🟢 正常運作</code>
<code>監控間隔: {config.monitoring.polling_interval}秒</code>
"""
        
        return dashboard
    
    def generate_compact_dashboard(self) -> str:
        """
        生成精簡版儀表板
        
        Returns:
            精簡儀表板 HTML
        """
        self.last_update = datetime.now()
        update_time = self.last_update.strftime("%H:%M:%S")
        
        try:
            # 獲取關鍵數據
            metrics = self.resource_monitor.get_current_metrics()
            active_sessions = len(self.session_tracker.get_active_sessions())
            total_sessions = self.session_tracker.get_session_count()
            
            # 構建精簡儀表板
            dashboard = f"""
<b>📊 監控摘要 [{update_time}]</b>
├─ 🖥️ CPU: {metrics.cpu_percent:.1f}%
├─ 💾 記憶體: {metrics.memory_percent:.1f}%
├─ 💿 磁碟: {metrics.disk_percent:.1f}%
└─ 🤖 會話: {active_sessions}/{total_sessions} 活動中
"""
            
            return dashboard
            
        except Exception as e:
            return f"<b>⚠️ 監控錯誤:</b> {str(e)}"
    
    def generate_session_detail(self, session_id: str) -> str:
        """
        生成會話詳細資訊
        
        Args:
            session_id: 會話 ID
            
        Returns:
            會話詳細資訊 HTML
        """
        try:
            session = self.session_tracker.get_session(session_id)
            if not session:
                return f"<b>❌ 錯誤:</b> 找不到會話 {session_id}"
            
            detail = f"""
<b>🔍 會話詳細資訊</b>
{"=" * 35}
<b>ID:</b> {session.session_id}
<b>標籤:</b> {session.label}
<b>狀態:</b> {self.status_icons.get(session.status, "❓")} {session.status.value.upper()}
<b>開始時間:</b> {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}
<b>最後更新:</b> {session.last_update.strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # 運行時間
            runtime = datetime.now() - session.start_time
            days = runtime.days
            hours, remainder = divmod(runtime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                runtime_str = f"{days}天 {hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                runtime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            detail += f"<b>運行時間:</b> {runtime_str}\n"
            
            # 進度
            progress_bar = self.generate_progress_bar(session.progress)
            detail += f"<b>進度:</b> {progress_bar}\n"
            
            # 預計完成時間
            if session.estimated_completion:
                time_left = session.estimated_completion - datetime.now()
                if time_left.total_seconds() > 0:
                    hours_left = int(time_left.total_seconds() // 3600)
                    minutes_left = int((time_left.total_seconds() % 3600) // 60)
                    detail += f"<b>預計完成:</b> {hours_left}小時{minutes_left}分鐘後\n"
            
            # 元數據
            if session.metadata:
                detail += "\n<b>📋 元數據:</b>\n"
                for key, value in session.metadata.items():
                    if isinstance(value, dict):
                        value_str = json.dumps(value, ensure_ascii=False)[:50] + "..."
                    else:
                        value_str = str(value)[:100]
                    detail += f"  • <b>{key}:</b> {value_str}\n"
            
            return detail
            
        except Exception as e:
            return f"<b>❌ 錯誤:</b> {str(e)}"


# 測試函數
if __name__ == "__main__":
    print("測試 Telegram 儀表板生成器...")
    
    # 創建模擬數據
    from datetime import datetime
    
    class MockSessionTracker:
        def get_active_sessions(self, limit=10):
            return []
        
        def get_session_count(self):
            return 0
        
        def get_statistics(self):
            return {
                'today_sessions': 5,
                'completed_sessions': 10,
                'failed_sessions': 2,
                'avg_runtime_minutes': 15.5,
                'success_rate': 83.3
            }
        
        def get_session(self, session_id):
            return None
    
    class MockResourceMonitor:
        def get_current_metrics(self):
            from .resource_monitor import ResourceMetrics
            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=45.5,
                memory_percent=67.8,
                disk_percent=32.1,
                network_sent_mb=125.4,
                network_recv_mb=89.7,
                load_avg_1m=1.2
            )
    
    # 創建儀表板
    dashboard = TelegramDashboard(MockSessionTracker(), MockResourceMonitor())
    
    # 測試完整儀表板
    print("\n完整儀表板:")
    print(dashboard.generate_full_dashboard())
    
    # 測試精簡儀表板
    print("\n精簡儀表板:")
    print(dashboard.generate_compact_dashboard())
    
    print("\n測試完成！")