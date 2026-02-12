"""
會話追蹤模組 - 負責追蹤 OpenClaw 會話狀態和進度
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import requests

from data_store import SessionData, SessionStatus, data_store
from config import config

class TaskType(Enum):
    """任務類型枚舉"""
    GENERAL = "general"
    CODING = "coding"
    RESEARCH = "research"
    MONITORING = "monitoring"
    AUTOMATION = "automation"
    ANALYSIS = "analysis"

@dataclass
class TaskProgress:
    """任務進度追蹤"""
    total_steps: int
    completed_steps: int
    current_step: str
    estimated_time_remaining: Optional[timedelta] = None
    last_step_time: Optional[datetime] = None
    
    @property
    def progress_percentage(self) -> float:
        """計算進度百分比"""
        if self.total_steps == 0:
            return 0.0
        return min(1.0, self.completed_steps / self.total_steps)
    
    def update_step(self, step_name: str, is_completed: bool = False):
        """更新步驟"""
        self.current_step = step_name
        self.last_step_time = datetime.now()
        
        if is_completed:
            self.completed_steps += 1
    
    def estimate_completion(self) -> Optional[datetime]:
        """估計完成時間"""
        if not self.last_step_time or self.completed_steps == 0:
            return None
        
        if self.completed_steps >= self.total_steps:
            return datetime.now()
        
        # 計算平均每步時間
        elapsed = datetime.now() - self.last_step_time
        avg_time_per_step = elapsed.total_seconds() / max(1, self.completed_steps)
        
        # 估計剩餘時間
        remaining_steps = self.total_steps - self.completed_steps
        estimated_seconds = avg_time_per_step * remaining_steps
        
        self.estimated_time_remaining = timedelta(seconds=estimated_seconds)
        return datetime.now() + self.estimated_time_remaining

class SessionTracker:
    """會話追蹤器"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.task_progress: Dict[str, TaskProgress] = {}
        self.lock = threading.RLock()
        self.running = False
        self.polling_thread: Optional[threading.Thread] = None
    
    def start_polling(self, interval: int = None):
        """開始輪詢會話狀態"""
        if self.running:
            return
        
        if interval is None:
            interval = config.monitoring.polling_interval
        
        self.running = True
        self.polling_thread = threading.Thread(
            target=self._polling_loop,
            args=(interval,),
            daemon=True
        )
        self.polling_thread.start()
        print(f"會話追蹤器已啟動，輪詢間隔: {interval}秒")
    
    def stop_polling(self):
        """停止輪詢"""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        print("會話追蹤器已停止")
    
    def _polling_loop(self, interval: int):
        """輪詢循環"""
        while self.running:
            try:
                self.update_sessions()
                time.sleep(interval)
            except Exception as e:
                print(f"輪詢錯誤: {e}")
                time.sleep(min(interval, 5))  # 錯誤時短暫等待
    
    def update_sessions(self):
        """更新所有會話狀態"""
        try:
            # 從 OpenClaw Gateway 獲取會話列表
            sessions = self._fetch_openclaw_sessions()
            
            with self.lock:
                for session_info in sessions:
                    self._process_session(session_info)
                
                # 清理不存在的會話
                current_ids = {s['id'] for s in sessions}
                for session_id in list(self.sessions.keys()):
                    if session_id not in current_ids:
                        # 標記為已完成
                        if session_id in self.sessions:
                            old_session = self.sessions[session_id]
                            if old_session.status == SessionStatus.ACTIVE:
                                old_session.status = SessionStatus.COMPLETED
                                old_session.last_update = datetime.now()
                                data_store.save_session(old_session)
                        
                        # 從記憶體中移除
                        self.sessions.pop(session_id, None)
                        self.task_progress.pop(session_id, None)
            
            print(f"已更新 {len(sessions)} 個會話")
            
        except Exception as e:
            print(f"更新會話失敗: {e}")
    
    def _fetch_openclaw_sessions(self) -> List[Dict[str, Any]]:
        """從 OpenClaw Gateway 獲取會話列表"""
        try:
            # 這裡需要根據 OpenClaw API 實際端點調整
            # 假設端點為 /api/sessions
            response = requests.get(
                f"{config.openclaw.gateway_url}/api/sessions",
                timeout=config.openclaw.timeout
            )
            
            if response.status_code == 200:
                return response.json().get('sessions', [])
            else:
                print(f"OpenClaw API 錯誤: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"連接 OpenClaw Gateway 失敗: {e}")
            return []
        except Exception as e:
            print(f"解析會話數據失敗: {e}")
            return []
    
    def _process_session(self, session_info: Dict[str, Any]):
        """處理單個會話信息"""
        session_id = session_info.get('id', '')
        if not session_id:
            return
        
        # 解析會話信息
        label = session_info.get('label', '未命名會話')
        status_str = session_info.get('status', 'unknown')
        
        # 轉換狀態
        status_map = {
            'active': SessionStatus.ACTIVE,
            'completed': SessionStatus.COMPLETED,
            'failed': SessionStatus.FAILED,
            'paused': SessionStatus.PAUSED,
            'queued': SessionStatus.QUEUED
        }
        status = status_map.get(status_str.lower(), SessionStatus.ACTIVE)
        
        # 獲取或創建任務進度
        if session_id not in self.task_progress:
            # 根據會話類型初始化任務進度
            task_type = self._detect_task_type(label, session_info)
            total_steps = self._estimate_total_steps(task_type)
            self.task_progress[session_id] = TaskProgress(
                total_steps=total_steps,
                completed_steps=0,
                current_step="初始化"
            )
        
        # 更新任務進度
        progress_tracker = self.task_progress[session_id]
        
        # 根據會話活動更新進度
        self._update_progress_from_session(progress_tracker, session_info)
        
        # 計算進度和估計完成時間
        progress = progress_tracker.progress_percentage
        estimated_completion = progress_tracker.estimate_completion()
        
        # 創建或更新會話數據
        session_data = SessionData(
            session_id=session_id,
            label=label,
            status=status,
            progress=progress,
            start_time=datetime.fromisoformat(session_info.get('created_at', datetime.now().isoformat())),
            last_update=datetime.now(),
            estimated_completion=estimated_completion,
            metadata={
                'task_type': session_info.get('task_type', 'unknown'),
                'channel': session_info.get('channel', 'unknown'),
                'model': session_info.get('model', 'unknown'),
                'agent': session_info.get('agent', 'unknown')
            }
        )
        
        # 保存到數據存儲
        self.sessions[session_id] = session_data
        data_store.save_session(session_data)
    
    def _detect_task_type(self, label: str, session_info: Dict[str, Any]) -> TaskType:
        """檢測任務類型"""
        label_lower = label.lower()
        
        if any(keyword in label_lower for keyword in ['code', 'program', 'script', '開發']):
            return TaskType.CODING
        elif any(keyword in label_lower for keyword in ['research', 'search', '研究', '調查']):
            return TaskType.RESEARCH
        elif any(keyword in label_lower for keyword in ['monitor', 'track', '監控', '追蹤']):
            return TaskType.MONITORING
        elif any(keyword in label_lower for keyword in ['automate', '自動化', 'bot']):
            return TaskType.AUTOMATION
        elif any(keyword in label_lower for keyword in ['analyze', 'analysis', '分析', '解析']):
            return TaskType.ANALYSIS
        else:
            return TaskType.GENERAL
    
    def _estimate_total_steps(self, task_type: TaskType) -> int:
        """根據任務類型估計總步驟數"""
        step_estimates = {
            TaskType.GENERAL: 5,
            TaskType.CODING: 8,
            TaskType.RESEARCH: 6,
            TaskType.MONITORING: 4,
            TaskType.AUTOMATION: 7,
            TaskType.ANALYSIS: 6
        }
        return step_estimates.get(task_type, 5)
    
    def _update_progress_from_session(self, progress: TaskProgress, session_info: Dict[str, Any]):
        """根據會話信息更新進度"""
        # 這裡可以根據實際的會話活動來更新進度
        # 例如：檢查工具調用次數、消息數量等
        
        # 簡單的進度更新邏輯
        messages = session_info.get('messages', [])
        tool_calls = session_info.get('tool_calls', [])
        
        # 根據消息和工具調用估算進度
        total_actions = len(messages) + len(tool_calls)
        
        if total_actions > 0:
            # 假設每個會話平均有 10-20 個動作
            estimated_total_actions = 15
            progress.completed_steps = min(
                progress.total_steps,
                int((total_actions / estimated_total_actions) * progress.total_steps)
            )
            
            # 更新當前步驟
            if tool_calls:
                last_tool = tool_calls[-1].get('tool', 'unknown')
                progress.current_step = f"執行工具: {last_tool}"
            elif messages:
                last_msg = messages[-1].get('role', 'unknown')
                progress.current_step = f"{last_msg} 回應"
    
    def get_active_sessions(self) -> List[SessionData]:
        """獲取活躍會話列表"""
        with self.lock:
            return [
                session for session in self.sessions.values()
                if session.status == SessionStatus.ACTIVE
            ]
    
    def get_session_stats(self) -> Dict[str, Any]:
        """獲取會話統計數據"""
        with self.lock:
            stats = {
                'total': len(self.sessions),
                'active': 0,
                'completed': 0,
                'failed': 0,
                'paused': 0,
                'queued': 0,
                'avg_progress': 0.0
            }
            
            total_progress = 0.0
            for session in self.sessions.values():
                stats[session.status.value] += 1
                total_progress += session.progress
            
            if stats['total'] > 0:
                stats['avg_progress'] = total_progress / stats['total']
            
            return stats
    
    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """獲取會話詳細信息"""
        with self.lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            progress = self.task_progress.get(session_id)
            
            details = session.to_dict()
            if progress:
                details['task_progress'] = {
                    'total_steps': progress.total_steps,
                    'completed_steps': progress.completed_steps,
                    'current_step': progress.current_step,
                    'estimated_time_remaining': str(progress.estimated_time_remaining) if progress.estimated_time_remaining else None
                }
            
            return details
    
    def manual_update_progress(self, session_id: str, progress_percentage: float, current_step: str = None):
        """手動更新會話進度"""
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            session.progress = max(0.0, min(1.0, progress_percentage))
            session.last_update = datetime.now()
            
            if current_step and session_id in self.task_progress:
                self.task_progress[session_id].current_step = current_step
            
            data_store.save_session(session)
            return True

# 全局會話追蹤器實例
session_tracker = SessionTracker()

if __name__ == "__main__":
    # 測試會話追蹤器
    tracker = SessionTracker()
    
    # 測試數據
    test_sessions = [
        {
            'id': 'test-1',
            'label': '編寫 Python 腳本',
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'task_type': 'coding',
            'channel': 'telegram',
            'messages': ['Hello', 'How can I help?'],
            'tool_calls': [{'tool': 'exec', 'args': {'command': 'ls'}}]
        },
        {
            'id': 'test-2',
            'label': '研究市場趨勢',
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'task_type': 'research',
            'channel': 'discord',
            'messages': ['Research request'],
            'tool_calls': []
        }
    ]
    
    # 模擬處理會話
    for session_info in test_sessions:
        tracker._process_session(session_info)
    
    # 獲取統計數據
    stats = tracker.get_session_stats()
    print(f"會話統計: {stats}")
    
    # 獲取活躍會話
    active_sessions = tracker.get_active_sessions()
    print(f"活躍會話數: {len(active_sessions)}")
    
    for session in active_sessions:
        print(f"  - {session.label}: {session.progress*100:.1f}%")