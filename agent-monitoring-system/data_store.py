"""
數據存儲模組 - 負責監控數據的存儲和管理
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
import gzip

class SessionStatus(Enum):
    """會話狀態枚舉"""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    QUEUED = "queued"

@dataclass
class SessionData:
    """會話數據結構"""
    session_id: str
    label: str
    status: SessionStatus
    progress: float  # 0.0 到 1.0
    start_time: datetime
    last_update: datetime
    estimated_completion: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not isinstance(self.status, SessionStatus):
            self.status = SessionStatus(self.status)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['start_time'] = self.start_time.isoformat()
        data['last_update'] = self.last_update.isoformat()
        if self.estimated_completion:
            data['estimated_completion'] = self.estimated_completion.isoformat()
        return data

@dataclass
class ResourceData:
    """資源數據結構"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int  # bytes
    network_recv: int  # bytes
    active_sessions: int
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'network_sent': self.network_sent,
            'network_recv': self.network_recv,
            'active_sessions': self.active_sessions
        }

@dataclass
class AlertData:
    """警報數據結構"""
    alert_id: str
    level: str  # info, warning, critical
    message: str
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.acknowledged_at:
            data['acknowledged_at'] = self.acknowledged_at.isoformat()
        return data

class DataStore:
    """數據存儲管理器"""
    
    def __init__(self, db_path: str = "monitoring.db", retention_days: int = 7):
        """
        初始化數據存儲
        
        Args:
            db_path: 數據庫文件路徑
            retention_days: 數據保留天數
        """
        self.db_path = db_path
        self.retention_days = retention_days
        self.lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """初始化數據庫表結構"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 建立會話表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    label TEXT,
                    status TEXT,
                    progress REAL,
                    start_time TIMESTAMP,
                    last_update TIMESTAMP,
                    estimated_completion TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # 建立資源監控表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    network_sent INTEGER,
                    network_recv INTEGER,
                    active_sessions INTEGER
                )
            ''')
            
            # 建立警報表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    level TEXT,
                    message TEXT,
                    timestamp TIMESTAMP,
                    acknowledged BOOLEAN,
                    acknowledged_by TEXT,
                    acknowledged_at TIMESTAMP
                )
            ''')
            
            # 建立索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_timestamp ON resources(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
            
            conn.commit()
            conn.close()
    
    def save_session(self, session: SessionData) -> bool:
        """保存會話數據"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO sessions 
                    (session_id, label, status, progress, start_time, last_update, estimated_completion, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.session_id,
                    session.label,
                    session.status.value,
                    session.progress,
                    session.start_time.isoformat(),
                    session.last_update.isoformat(),
                    session.estimated_completion.isoformat() if session.estimated_completion else None,
                    json.dumps(session.metadata)
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"保存會話數據失敗: {e}")
                return False
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """獲取會話數據"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return self._row_to_session(row)
                return None
            except Exception as e:
                print(f"獲取會話數據失敗: {e}")
                return None
    
    def get_all_sessions(self, status: Optional[SessionStatus] = None) -> List[SessionData]:
        """獲取所有會話數據"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if status:
                    cursor.execute('SELECT * FROM sessions WHERE status = ? ORDER BY last_update DESC', (status.value,))
                else:
                    cursor.execute('SELECT * FROM sessions ORDER BY last_update DESC')
                
                rows = cursor.fetchall()
                conn.close()
                
                return [self._row_to_session(row) for row in rows]
            except Exception as e:
                print(f"獲取所有會話數據失敗: {e}")
                return []
    
    def save_resource_data(self, resource: ResourceData) -> bool:
        """保存資源數據"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO resources 
                    (timestamp, cpu_percent, memory_percent, disk_percent, network_sent, network_recv, active_sessions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    resource.timestamp.isoformat(),
                    resource.cpu_percent,
                    resource.memory_percent,
                    resource.disk_percent,
                    resource.network_sent,
                    resource.network_recv,
                    resource.active_sessions
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"保存資源數據失敗: {e}")
                return False
    
    def get_resource_history(self, hours: int = 24, limit: int = 100) -> List[ResourceData]:
        """獲取資源歷史數據"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                cursor.execute('''
                    SELECT * FROM resources 
                    WHERE timestamp >= ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (cutoff, limit))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [self._row_to_resource(row) for row in rows]
            except Exception as e:
                print(f"獲取資源歷史數據失敗: {e}")
                return []
    
    def save_alert(self, alert: AlertData) -> bool:
        """保存警報"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO alerts 
                    (alert_id, level, message, timestamp, acknowledged, acknowledged_by, acknowledged_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert.alert_id,
                    alert.level,
                    alert.message,
                    alert.timestamp.isoformat(),
                    alert.acknowledged,
                    alert.acknowledged_by,
                    alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"保存警報失敗: {e}")
                return False
    
    def get_unacknowledged_alerts(self) -> List[AlertData]:
        """獲取未確認的警報"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM alerts WHERE acknowledged = 0 ORDER BY timestamp DESC')
                rows = cursor.fetchall()
                conn.close()
                
                return [self._row_to_alert(row) for row in rows]
            except Exception as e:
                print(f"獲取未確認警報失敗: {e}")
                return []
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """確認警報"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE alerts 
                    SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = ?
                    WHERE alert_id = ?
                ''', (acknowledged_by, datetime.now().isoformat(), alert_id))
                
                conn.commit()
                conn.close()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"確認警報失敗: {e}")
                return False
    
    def cleanup_old_data(self):
        """清理舊數據"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 清理舊的資源數據
                cutoff = (datetime.now() - timedelta(days=self.retention_days)).isoformat()
                cursor.execute('DELETE FROM resources WHERE timestamp < ?', (cutoff,))
                
                # 清理已確認的舊警報
                cursor.execute('DELETE FROM alerts WHERE acknowledged = 1 AND timestamp < ?', (cutoff,))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"清理舊數據失敗: {e}")
                return False
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計數據"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                stats = {}
                
                # 會話統計
                cursor.execute('SELECT status, COUNT(*) FROM sessions GROUP BY status')
                session_stats = {row[0]: row[1] for row in cursor.fetchall()}
                stats['sessions'] = session_stats
                
                # 資源數據統計
                cursor.execute('SELECT COUNT(*) FROM resources')
                stats['resource_records'] = cursor.fetchone()[0]
                
                # 警報統計
                cursor.execute('SELECT level, COUNT(*) FROM alerts WHERE acknowledged = 0 GROUP BY level')
                alert_stats = {row[0]: row[1] for row in cursor.fetchall()}
                stats['active_alerts'] = alert_stats
                
                conn.close()
                return stats
            except Exception as e:
                print(f"獲取統計數據失敗: {e}")
                return {}
    
    def _row_to_session(self, row) -> SessionData:
        """將數據庫行轉換為 SessionData"""
        return SessionData(
            session_id=row[0],
            label=row[1],
            status=SessionStatus(row[2]),
            progress=row[3],
            start_time=datetime.fromisoformat(row[4]),
            last_update=datetime.fromisoformat(row[5]),
            estimated_completion=datetime.fromisoformat(row[6]) if row[6] else None,
            metadata=json.loads(row[7]) if row[7] else {}
        )
    
    def _row_to_resource(self, row) -> ResourceData:
        """將數據庫行轉換為 ResourceData"""
        return ResourceData(
            timestamp=datetime.fromisoformat(row[1]),
            cpu_percent=row[2],
            memory_percent=row[3],
            disk_percent=row[4],
            network_sent=row[5],
            network_recv=row[6],
            active_sessions=row[7]
        )
    
    def _row_to_alert(self, row) -> AlertData:
        """將數據庫行轉換為 AlertData"""
        return AlertData(
            alert_id=row[0],
            level=row[1],
            message=row[2],
            timestamp=datetime.fromisoformat(row[3]),
            acknowledged=bool(row[4]),
            acknowledged_by=row[5],
            acknowledged_at=datetime.fromisoformat(row[6]) if row[6] else None
        )
    
    def __del__(self):
        """析構函數，清理資源"""
        self.cleanup_old_data()

# 全局數據存儲實例
data_store = DataStore()

if __name__ == "__main__":
    # 測試數據存儲
    store = DataStore("test.db")
    
    # 測試會話數據
    session = SessionData(
        session_id="test-123",
        label="測試會話",
        status=SessionStatus.ACTIVE,
        progress=0.5,
        start_time=datetime.now(),
        last_update=datetime.now(),
        metadata={"test": True}
    )
    
    store.save_session(session)
    retrieved = store.get_session("test-123")
    print(f"檢索到的會話: {retrieved}")
    
    # 測試資源數據
    resource = ResourceData(
        timestamp=datetime.now(),
        cpu_percent=25.5,
        memory_percent=45.2,
        disk_percent=60.1,
        network_sent=1024,
        network_recv=2048,
        active_sessions=3
    )
    
    store.save_resource_data(resource)
    history = store.get_resource_history()
    print(f"資源歷史記錄數: {len(history)}")
    
    # 測試統計數據
    stats = store.get_stats()
    print(f"統計數據: {stats}")