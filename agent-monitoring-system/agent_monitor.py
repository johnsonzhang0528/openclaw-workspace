"""
主監控類別 - 整合所有模組、提供啟動/停止介面
"""

import time
import threading
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

# 相對導入改為絕對導入
try:
    # 嘗試作為套件導入
    from .config import config
    from .data_store import data_store, SessionStatus
    from .session_tracker import SessionTracker, session_tracker
    from .resource_monitor import ResourceMonitor, resource_monitor
    from .alert_system import AlertSystem, AlertLevel
    from .telegram_dashboard import TelegramDashboard
    from .integration import IntegrationManager
except ImportError:
    # 如果作為獨立腳本運行，使用直接導入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from config import config
    from data_store import data_store, SessionStatus
    from session_tracker import SessionTracker, session_tracker
    from resource_monitor import ResourceMonitor, resource_monitor
    from alert_system import AlertSystem, AlertLevel
    from telegram_dashboard import TelegramDashboard
    from integration import IntegrationManager

class AgentMonitor:
    """主監控類別 - 整合所有監控模組"""
    
    def __init__(self):
        """初始化監控系統"""
        print("初始化 Agent 監控系統...")
        
        # 初始化各模組
        self.session_tracker = session_tracker
        self.resource_monitor = resource_monitor
        self.alert_system = AlertSystem(session_tracker, resource_monitor)
        self.dashboard = TelegramDashboard(session_tracker, resource_monitor)
        self.integration = IntegrationManager(session_tracker, resource_monitor)
        
        # 狀態標誌
        self.running = False
        self.shutdown_requested = False
        self.main_thread: Optional[threading.Thread] = None
        
        # 統計數據
        self.start_time = datetime.now()
        self.monitoring_cycles = 0
        self.alerts_triggered = 0
        
        # 註冊信號處理
        self._register_signal_handlers()
        
        print("Agent 監控系統初始化完成")
    
    def _register_signal_handlers(self):
        """註冊信號處理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信號處理函數"""
        print(f"\n收到信號 {signum}，正在關閉監控系統...")
        self.shutdown_requested = True
        self.stop()
    
    def start(self):
        """啟動監控系統"""
        if self.running:
            print("監控系統已在運行中")
            return
        
        print("啟動 Agent 監控系統...")
        self.running = True
        self.shutdown_requested = False
        self.start_time = datetime.now()
        
        # 啟動各模組
        print("啟動會話追蹤器...")
        self.session_tracker.start_polling()
        
        print("啟動資源監控器...")
        self.resource_monitor.start_monitoring()
        
        print("啟動警報系統...")
        self.alert_system.start_monitoring()
        
        print("啟動系統整合管理器...")
        try:
            # 嘗試啟動整合管理器
            if hasattr(self.integration, 'start'):
                self.integration.start()
            else:
                print("⚠️  整合管理器沒有 start 方法，跳過啟動")
        except Exception as e:
            print(f"⚠️  整合管理器啟動失敗: {e}")
        
        # 啟動主循環線程
        self.main_thread = threading.Thread(
            target=self._main_loop,
            daemon=True
        )
        self.main_thread.start()
        
        print("✅ Agent 監控系統已啟動")
        print(f"📊 配置: {config}")
    
    def stop(self):
        """停止監控系統"""
        if not self.running:
            print("監控系統未在運行中")
            return
        
        print("停止 Agent 監控系統...")
        self.running = False
        
        # 停止各模組
        print("停止警報系統...")
        self.alert_system.stop_monitoring()
        
        print("停止資源監控器...")
        self.resource_monitor.stop_monitoring()
        
        print("停止會話追蹤器...")
        self.session_tracker.stop_polling()
        
        print("停止系統整合管理器...")
        try:
            if hasattr(self.integration, 'stop'):
                self.integration.stop()
            else:
                print("⚠️  整合管理器沒有 stop 方法，跳過停止")
        except Exception as e:
            print(f"⚠️  整合管理器停止失敗: {e}")
        
        # 等待主線程結束
        if self.main_thread:
            self.main_thread.join(timeout=10)
        
        # 清理數據
        print("清理舊數據...")
        data_store.cleanup_old_data()
        
        print("✅ Agent 監控系統已停止")
    
    def _main_loop(self):
        """主監控循環"""
        print("主監控循環開始")
        
        last_dashboard_update = 0
        dashboard_interval = config.dashboard.refresh_interval
        
        while self.running and not self.shutdown_requested:
            try:
                current_time = time.time()
                self.monitoring_cycles += 1
                
                # 定期更新儀表板（如果配置了自動更新）
                if current_time - last_dashboard_update >= dashboard_interval:
                    self._update_dashboard()
                    last_dashboard_update = current_time
                
                # 檢查系統健康狀態
                if self.monitoring_cycles % 10 == 0:  # 每10個週期檢查一次
                    self._check_system_health()
                
                # 記錄統計數據
                if self.monitoring_cycles % 100 == 0:
                    self._log_statistics()
                
                # 短暫休眠
                time.sleep(1)
                
            except Exception as e:
                print(f"主監控循環錯誤: {e}")
                time.sleep(5)
        
        print("主監控循環結束")
    
    def _update_dashboard(self):
        """更新儀表板"""
        try:
            # 獲取當前警報
            active_alerts = self.alert_system.get_active_alerts()
            
            # 生成儀表板
            dashboard_html = self.dashboard.generate_full_dashboard(active_alerts)
            
            # 這裡可以將儀表板發送到 Telegram 或其他目的地
            # 目前先記錄到日誌
            if config.dashboard.enable_charts:
                print(f"儀表板更新 ({datetime.now().strftime('%H:%M:%S')}):")
                print(dashboard_html[:500] + "..." if len(dashboard_html) > 500 else dashboard_html)
                
        except Exception as e:
            print(f"更新儀表板失敗: {e}")
    
    def _check_system_health(self):
        """檢查系統健康狀態"""
        try:
            # 檢查資源健康
            resource_health = self.resource_monitor.check_resource_health()
            
            if resource_health['status'] != 'healthy':
                # 觸發警報
                for issue in resource_health.get('issues', []):
                    level = 'critical' if resource_health['status'] == 'critical' else 'warning'
                    self.alert_system.manual_alert(
                        level=level,
                        message=issue,
                        source="health_check"
                    )
                    self.alerts_triggered += 1
            
            # 檢查數據庫連接
            stats = data_store.get_stats()
            if not stats:
                self.alert_system.manual_alert(
                    level="warning",
                    message="數據庫連接異常",
                    source="health_check"
                )
            
        except Exception as e:
            print(f"檢查系統健康失敗: {e}")
    
    def _log_statistics(self):
        """記錄統計數據"""
        try:
            uptime = datetime.now() - self.start_time
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            stats = {
                'uptime': f"{uptime.days}天 {hours:02d}:{minutes:02d}:{seconds:02d}",
                'monitoring_cycles': self.monitoring_cycles,
                'alerts_triggered': self.alerts_triggered,
                'session_stats': self.session_tracker.get_session_stats(),
                'resource_stats': self.resource_monitor.get_resource_stats(minutes=5),
                'alert_stats': self.alert_system.get_alert_stats(hours=1),
                'database_stats': data_store.get_stats()
            }
            
            print(f"\n📊 系統統計 (週期 {self.monitoring_cycles}):")
            print(f"  運行時間: {stats['uptime']}")
            print(f"  會話統計: {stats['session_stats']}")
            print(f"  警報觸發: {stats['alerts_triggered']} 次")
            
        except Exception as e:
            print(f"記錄統計數據失敗: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        status = {
            'running': self.running,
            'uptime': str(datetime.now() - self.start_time),
            'start_time': self.start_time.isoformat(),
            'monitoring_cycles': self.monitoring_cycles,
            'alerts_triggered': self.alerts_triggered,
            'modules': {
                'session_tracker': self.session_tracker.running if hasattr(self.session_tracker, 'running') else False,
                'resource_monitor': self.resource_monitor.running if hasattr(self.resource_monitor, 'running') else False,
                'alert_system': self.alert_system.running if hasattr(self.alert_system, 'running') else False,
                'integration': self.integration.running if hasattr(self.integration, 'running') else False
            },
            'config_summary': config.to_dict()
        }
        
        # 添加各模組詳細狀態
        try:
            status['session_stats'] = self.session_tracker.get_session_stats()
            status['resource_health'] = self.resource_monitor.check_resource_health()
            status['active_alerts'] = len(self.alert_system.get_active_alerts())
            status['database_stats'] = data_store.get_stats()
        except Exception as e:
            status['error'] = f"獲取詳細狀態失敗: {e}"
        
        return status
    
    def get_dashboard(self, compact: bool = False) -> str:
        """獲取儀表板內容"""
        try:
            active_alerts = self.alert_system.get_active_alerts()
            
            if compact:
                return self.dashboard.generate_compact_dashboard()
            else:
                return self.dashboard.generate_full_dashboard(active_alerts)
                
        except Exception as e:
            return f"<b>❌ 錯誤:</b> 生成儀表板失敗: {str(e)}"
    
    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """獲取會話詳細信息"""
        return self.session_tracker.get_session_details(session_id)
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "user") -> bool:
        """確認警報"""
        return self.alert_system.acknowledge_alert(alert_id, acknowledged_by)
    
    def manual_alert(self, level: str, message: str) -> bool:
        """手動觸發警報"""
        return self.alert_system.manual_alert(level, message, "manual")
    
    def get_system_info(self) -> Dict[str, Any]:
        """獲取系統信息"""
        return self.resource_monitor.get_system_info()
    
    def cleanup(self):
        """清理資源"""
        print("清理監控系統資源...")
        self.stop()
        
        # 清理數據庫連接等資源
        # data_store 會在析構時自動清理
        
        print("資源清理完成")
    
    def __enter__(self):
        """上下文管理器進入"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.cleanup()

# 全局監控實例
agent_monitor = AgentMonitor()

def start_monitoring():
    """啟動監控系統（方便導入使用）"""
    agent_monitor.start()

def stop_monitoring():
    """停止監控系統（方便導入使用）"""
    agent_monitor.stop()

def get_status():
    """獲取系統狀態（方便導入使用）"""
    return agent_monitor.get_status()

if __name__ == "__main__":
    print("測試 Agent 監控系統...")
    
    # 創建監控實例
    monitor = AgentMonitor()
    
    try:
        # 啟動監控
        monitor.start()
        
        # 運行一段時間
        print("\n監控系統運行中，按 Ctrl+C 停止...")
        
        # 顯示初始狀態
        status = monitor.get_status()
        print(f"\n初始狀態: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
        # 等待用戶中斷
        import time
        for i in range(30):  # 運行30秒
            if monitor.shutdown_requested:
                break
            time.sleep(1)
            
            # 每10秒顯示一次儀表板
            if i % 10 == 0:
                print(f"\n儀表板 (第{i}秒):")
                print(monitor.get_dashboard(compact=True))
        
    except KeyboardInterrupt:
        print("\n收到中斷信號")
    finally:
        # 停止監控
        monitor.stop()
        
        # 顯示最終狀態
        final_status = monitor.get_status()
        print(f"\n最終狀態: {json.dumps(final_status, indent=2, ensure_ascii=False)}")
    
    print("\n測試完成！")