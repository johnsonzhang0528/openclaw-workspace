"""
系統整合模組 - 整合議題追蹤系統和 OpenClaw 會話管理
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import os

# 相對導入改為絕對導入
try:
    from config import config
    from data_store import data_store, SessionData, SessionStatus
    from session_tracker import SessionTracker
    from resource_monitor import ResourceMonitor
except ImportError:
    # 用於直接執行測試
    config = type('Config', (), {})()
    config.integration = type('IntegrationConfig', (), {
        'enable_issue_tracker': True,
        'enable_openclaw_sessions': True
    })()
    
    class MockDataStore:
        pass
    
    data_store = MockDataStore()
    SessionStatus = type('SessionStatus', (), {
        'COMPLETED': 'completed',
        'FAILED': 'failed'
    })()
    SessionData = type('SessionData', (), {})
    SessionTracker = type('SessionTracker', (), {})
    ResourceMonitor = type('ResourceMonitor', (), {})

@dataclass
class IssueData:
    """議題數據結構"""
    issue_id: str
    title: str
    status: str  # open, closed, in_progress
    created_at: datetime
    updated_at: datetime
    labels: List[str]
    participants: List[str]
    message_count: int
    last_message: Optional[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IssueData':
        """從字典創建議題數據"""
        return cls(
            issue_id=data.get('id', ''),
            title=data.get('title', ''),
            status=data.get('status', 'open'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
            labels=data.get('labels', []),
            participants=data.get('participants', []),
            message_count=data.get('message_count', 0),
            last_message=data.get('last_message')
        )

class IssueTrackerIntegration:
    """議題追蹤系統整合"""
    
    def __init__(self, issue_file_path: str = None):
        """
        初始化議題追蹤整合
        
        Args:
            issue_file_path: 議題追蹤系統檔案路徑
        """
        if issue_file_path is None:
            # 預設路徑
            self.issue_file_path = "/root/.openclaw/workspace/issue_tracker_system.md"
        else:
            self.issue_file_path = issue_file_path
        
        self.issues: Dict[str, IssueData] = {}
        self.last_load_time: Optional[datetime] = None
        
    def load_issues(self) -> bool:
        """
        載入議題數據
        
        Returns:
            是否成功載入
        """
        try:
            if not os.path.exists(self.issue_file_path):
                print(f"議題檔案不存在: {self.issue_file_path}")
                return False
            
            # 讀取檔案
            with open(self.issue_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析議題數據（這裡需要根據實際格式調整）
            # 目前假設檔案包含 JSON 格式的議題數據
            issues_data = self._parse_issue_file(content)
            
            # 轉換為 IssueData 對象
            self.issues = {}
            for issue_id, issue_dict in issues_data.items():
                self.issues[issue_id] = IssueData.from_dict(issue_dict)
            
            self.last_load_time = datetime.now()
            print(f"已載入 {len(self.issues)} 個議題")
            return True
            
        except Exception as e:
            print(f"載入議題失敗: {e}")
            return False
    
    def _parse_issue_file(self, content: str) -> Dict[str, Any]:
        """
        解析議題檔案內容
        
        Args:
            content: 檔案內容
            
        Returns:
            議題數據字典
        """
        # 這裡需要根據實際的議題追蹤系統格式進行解析
        # 目前返回空字典，需要根據實際格式實現
        return {}
    
    def get_open_issues(self) -> List[IssueData]:
        """
        獲取開啟中的議題
        
        Returns:
            開啟議題列表
        """
        return [issue for issue in self.issues.values() if issue.status == 'open']
    
    def get_issues_by_label(self, label: str) -> List[IssueData]:
        """
        根據標籤獲取議題
        
        Args:
            label: 標籤名稱
            
        Returns:
            議題列表
        """
        return [issue for issue in self.issues.values() if label in issue.labels]
    
    def get_recent_issues(self, hours: int = 24) -> List[IssueData]:
        """
        獲取最近更新的議題
        
        Args:
            hours: 時間範圍（小時）
            
        Returns:
            議題列表
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return [issue for issue in self.issues.values() if issue.updated_at >= cutoff]
    
    def get_issue_stats(self) -> Dict[str, Any]:
        """
        獲取議題統計數據
        
        Returns:
            統計數據字典
        """
        open_issues = self.get_open_issues()
        recent_issues = self.get_recent_issues(24)
        
        # 標籤統計
        label_stats = {}
        for issue in self.issues.values():
            for label in issue.labels:
                label_stats[label] = label_stats.get(label, 0) + 1
        
        return {
            'total_issues': len(self.issues),
            'open_issues': len(open_issues),
            'recent_issues_24h': len(recent_issues),
            'label_stats': label_stats,
            'last_updated': self.last_load_time.isoformat() if self.last_load_time else None
        }

class OpenClawSessionIntegration:
    """OpenClaw 會話管理整合"""
    
    def __init__(self, session_tracker: SessionTracker):
        """
        初始化 OpenClaw 會話整合
        
        Args:
            session_tracker: 會話追蹤器實例
        """
        self.session_tracker = session_tracker
        
    def sync_with_openclaw_sessions(self) -> Dict[str, Any]:
        """
        與 OpenClaw 會話同步
        
        Returns:
            同步結果
        """
        try:
            # 這裡可以調用 OpenClaw 的 sessions_list API
            # 目前使用 session_tracker 的數據
            
            active_sessions = self.session_tracker.get_active_sessions()
            all_sessions = self.session_tracker.get_all_sessions()
            
            # 統計數據
            stats = {
                'total_sessions': len(all_sessions),
                'active_sessions': len(active_sessions),
                'completed_sessions': len([s for s in all_sessions if s.status == SessionStatus.COMPLETED]),
                'failed_sessions': len([s for s in all_sessions if s.status == SessionStatus.FAILED]),
                'sync_time': datetime.now().isoformat()
            }
            
            # 更新會話數據
            for session in active_sessions:
                # 這裡可以添加與 OpenClaw API 的同步邏輯
                pass
            
            return {
                'success': True,
                'stats': stats,
                'message': f"已同步 {len(all_sessions)} 個會話"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '同步失敗'
            }
    
    def get_session_insights(self) -> Dict[str, Any]:
        """
        獲取會話洞察分析
        
        Returns:
            洞察數據
        """
        sessions = self.session_tracker.get_all_sessions()
        
        if not sessions:
            return {'total_sessions': 0, 'insights': []}
        
        # 分析會話模式
        insights = []
        
        # 1. 最活躍的時間段
        hour_counts = {}
        for session in sessions:
            hour = session.start_time.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        if hour_counts:
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])
            insights.append({
                'type': 'peak_usage',
                'hour': peak_hour[0],
                'count': peak_hour[1],
                'message': f'最活躍時段: {peak_hour[0]:02d}:00 ({peak_hour[1]} 個會話)'
            })
        
        # 2. 平均完成時間
        completed_sessions = [s for s in sessions if s.status == SessionStatus.COMPLETED]
        if completed_sessions:
            total_duration = sum(
                (s.last_update - s.start_time).total_seconds() 
                for s in completed_sessions 
                if s.last_update
            )
            avg_duration = total_duration / len(completed_sessions)
            insights.append({
                'type': 'avg_completion',
                'seconds': avg_duration,
                'message': f'平均完成時間: {avg_duration/60:.1f} 分鐘'
            })
        
        # 3. 成功率
        total_ended = len([s for s in sessions if s.status in [SessionStatus.COMPLETED, SessionStatus.FAILED]])
        if total_ended > 0:
            success_count = len([s for s in sessions if s.status == SessionStatus.COMPLETED])
            success_rate = (success_count / total_ended) * 100
            insights.append({
                'type': 'success_rate',
                'rate': success_rate,
                'message': f'成功率: {success_rate:.1f}%'
            })
        
        return {
            'total_sessions': len(sessions),
            'insights': insights,
            'generated_at': datetime.now().isoformat()
        }

class IntegrationManager:
    """整合管理器 - 管理所有系統整合"""
    
    def __init__(self, session_tracker: SessionTracker, resource_monitor: ResourceMonitor):
        """
        初始化整合管理器
        
        Args:
            session_tracker: 會話追蹤器
            resource_monitor: 資源監控器
        """
        self.session_tracker = session_tracker
        self.resource_monitor = resource_monitor
        
        # 初始化各整合模組
        self.issue_tracker = IssueTrackerIntegration()
        self.openclaw_integration = OpenClawSessionIntegration(session_tracker)
        
        # 整合狀態
        self.integrations_enabled = {
            'issue_tracker': config.integration.enable_issue_tracker,
            'openclaw_sessions': config.integration.enable_openclaw_sessions
        }
        
        print("整合管理器初始化完成")
    
    def initialize_integrations(self) -> Dict[str, Any]:
        """
        初始化所有整合
        
        Returns:
            初始化結果
        """
        results = {}
        
        # 初始化議題追蹤
        if self.integrations_enabled['issue_tracker']:
            try:
                success = self.issue_tracker.load_issues()
                results['issue_tracker'] = {
                    'success': success,
                    'message': f'議題追蹤整合 {"成功" if success else "失敗"}'
                }
            except Exception as e:
                results['issue_tracker'] = {
                    'success': False,
                    'error': str(e),
                    'message': '議題追蹤整合失敗'
                }
        
        # 初始化 OpenClaw 會話整合
        if self.integrations_enabled['openclaw_sessions']:
            try:
                sync_result = self.openclaw_integration.sync_with_openclaw_sessions()
                results['openclaw_sessions'] = sync_result
            except Exception as e:
                results['openclaw_sessions'] = {
                    'success': False,
                    'error': str(e),
                    'message': 'OpenClaw 會話整合失敗'
                }
        
        return results
    
    def get_integration_status(self) -> Dict[str, Any]:
        """
        獲取整合狀態
        
        Returns:
            狀態信息
        """
        status = {
            'integrations_enabled': self.integrations_enabled,
            'issue_tracker': {
                'loaded': len(self.issue_tracker.issues) > 0,
                'issue_count': len(self.issue_tracker.issues),
                'last_load': self.issue_tracker.last_load_time.isoformat() if self.issue_tracker.last_load_time else None
            },
            'openclaw_sessions': {
                'active': True,
                'session_count': len(self.session_tracker.get_all_sessions())
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return status
    
    def refresh_integrations(self) -> Dict[str, Any]:
        """
        刷新所有整合數據
        
        Returns:
            刷新結果
        """
        results = {}
        
        # 刷新議題數據
        if self.integrations_enabled['issue_tracker']:
            success = self.issue_tracker.load_issues()
            results['issue_tracker'] = {
                'success': success,
                'message': f'議題數據刷新 {"成功" if success else "失敗"}'
            }
        
        # 刷新會話數據
        if self.integrations_enabled['openclaw_sessions']:
            sync_result = self.openclaw_integration.sync_with_openclaw_sessions()
            results['openclaw_sessions'] = sync_result
        
        results['timestamp'] = datetime.now().isoformat()
        return results
    
    def get_combined_dashboard_data(self) -> Dict[str, Any]:
        """
        獲取整合的儀表板數據
        
        Returns:
            整合數據
        """
        data = {
            'system': {
                'timestamp': datetime.now().isoformat(),
                'integrations': self.get_integration_status()
            },
            'issues': {},
            'sessions': {},
            'insights': []
        }
        
        # 議題數據
        if self.integrations_enabled['issue_tracker'] and self.issue_tracker.issues:
            issue_stats = self.issue_tracker.get_issue_stats()
            data['issues'] = {
                'stats': issue_stats,
                'recent_issues': [
                    {
                        'id': issue.issue_id,
                        'title': issue.title,
                        'status': issue.status,
                        'updated': issue.updated_at.isoformat()
                    }
                    for issue in self.issue_tracker.get_recent_issues(6)[:5]  # 最近6小時，最多5個
                ]
            }
        
        # 會話數據
        if self.integrations_enabled['openclaw_sessions']:
            session_insights = self.openclaw_integration.get_session_insights()
            data['sessions'] = session_insights
            data['insights'].extend(session_insights.get('insights', []))
        
        # 添加系統建議
        data['insights'].extend(self._generate_system_insights())
        
        return data
    
    def _generate_system_insights(self) -> List[Dict[str, Any]]:
        """
        生成系統洞察建議
        
        Returns:
            洞察列表
        """
        insights = []
        
        # 檢查議題追蹤狀態
        if self.integrations_enabled['issue_tracker'] and not self.issue_tracker.issues:
            insights.append({
                'type': 'integration_warning',
                'level': 'warning',
                'message': '議題追蹤整合未載入數據，請檢查設定'
            })
        
        # 檢查會話數量
        session_count = len(self.session_tracker.get_all_sessions())
        if session_count > 50:
            insights.append({
                'type': 'high_session_count',
                'level': 'info',
                'message': f'會話數量較多: {session_count} 個，建議定期清理'
            })
        
        return insights
    
    def enable_integration(self, integration_name: str, enabled: bool = True) -> bool:
        """
        啟用或禁用整合
        
        Args:
            integration_name: 整合名稱
            enabled: 是否啟用
            
        Returns:
            是否成功
        """
        if integration_name in self.integrations_enabled:
            self.integrations_enabled[integration_name] = enabled
            
            # 如果啟用，立即初始化
            if enabled:
                if integration_name == 'issue_tracker':
                    self.issue_tracker.load_issues()
                elif integration_name == 'openclaw_sessions':
                    self.openclaw_integration.sync_with_openclaw_sessions()
            
            return True
        
        return False

# 全局整合管理器實例
integration_manager = None

def init_integration_manager(session_tracker: SessionTracker, resource_monitor: ResourceMonitor) -> IntegrationManager:
    """初始化整合管理器"""
    global integration_manager
    integration_manager = IntegrationManager(session_tracker, resource_monitor)
    return integration_manager

if __name__ == "__main__":
    print("測試系統整合模組...")
    
    # 創建模擬對象
    class MockSessionTracker:
        def get_all_sessions(self):
            return []
        def get_active_sessions(self):
            return []
    
    class MockResourceMonitor:
        pass
    
    # 創建整合管理器
    tracker = MockSessionTracker()
    monitor = MockResourceMonitor()
    manager = IntegrationManager(tracker, monitor)
    
    # 測試初始化
    print("初始化整合...")
    init_results = manager.initialize_integrations()
    print("初始化結果:")
    for key, value in init_results.items():
        print(f"  {key}: {value.get('message', 'N/A')}")
    
    # 測試狀態獲取
    print("\n整合狀態:")
    status = manager.get_integration_status()
    print(f"啟用的整合: {status.get('integrations_enabled', {})}")
    print(f"議題數量: {status.get('issue_tracker', {}).get('issue_count', 0)}")
    print(f"會話數量: {status.get('openclaw_sessions', {}).get('session_count', 0)}")
    
    # 測試儀表板數據
    print("\n儀表板數據:")
    dashboard_data = manager.get_combined_dashboard_data()
    print(f"數據鍵值: {list(dashboard_data.keys())}")
    
    print("\n測試完成！")