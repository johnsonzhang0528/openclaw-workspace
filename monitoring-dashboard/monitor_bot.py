#!/usr/bin/env python3
"""
OpenClaw 子代理任務監控腳本
簡化版本，專注於實際監控功能
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import yaml

class SubagentMonitor:
    """子代理監控器"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """初始化監控器"""
        self.config = self.load_config(config_path)
        self.sessions_cache = {}
        self.last_update = None
        
    def load_config(self, config_path: str) -> Dict:
        """載入配置檔案"""
        default_config = {
            'dashboard': {
                'refresh_interval': 30,
                'max_tasks': 20,
                'history_days': 7
            },
            'display': {
                'separator': '─',
                'max_width': 40,
                'status_icons': {
                    'running': '🟢',
                    'pending': '🟡',
                    'paused': '🟠',
                    'completed': '✅',
                    'failed': '🔴',
                    'stopped': '⚪'
                },
                'progress_bar': {
                    'length': 10,
                    'filled': '█',
                    'empty': '░'
                }
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                # 合併配置
                self.merge_config(default_config, config)
        except Exception as e:
            print(f"載入配置失敗: {e}")
        
        return default_config
    
    def merge_config(self, default: Dict, custom: Dict):
        """合併配置"""
        for key, value in custom.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self.merge_config(default[key], value)
            else:
                default[key] = value
    
    def get_subagent_sessions(self) -> List[Dict]:
        """獲取子代理會話列表"""
        try:
            # 嘗試使用 OpenClaw CLI
            result = subprocess.run(
                ["openclaw", "sessions", "list", "--json", "--kinds", "subagent"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                sessions = data.get("sessions", [])
                
                # 過濾出子代理會話
                subagents = []
                for session in sessions:
                    if "subagent" in session.get("key", ""):
                        subagents.append(session)
                
                self.sessions_cache = {s["key"]: s for s in subagents}
                self.last_update = datetime.now()
                return subagents
                
        except Exception as e:
            print(f"獲取會話列表失敗: {e}")
        
        # 返回緩存數據或空列表
        return list(self.sessions_cache.values())
    
    def get_system_info(self) -> Dict:
        """獲取系統資訊"""
        try:
            # CPU 使用率
            cpu_result = subprocess.run(
                ["top", "-bn1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # 記憶體使用
            mem_result = subprocess.run(
                ["free", "-h"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # 系統負載
            load_result = subprocess.run(
                ["cat", "/proc/loadavg"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return {
                "cpu": self.parse_cpu_usage(cpu_result.stdout),
                "memory": self.parse_memory_usage(mem_result.stdout),
                "load": self.parse_load_average(load_result.stdout),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"獲取系統資訊失敗: {e}")
            return {"cpu": "未知", "memory": "未知", "load": "未知", "timestamp": "未知"}
    
    def parse_cpu_usage(self, top_output: str) -> str:
        """解析 CPU 使用率"""
        try:
            for line in top_output.split('\n'):
                if '%Cpu(s):' in line:
                    parts = line.split(',')
                    if len(parts) >= 4:
                        idle_part = parts[3]
                        idle = float(idle_part.split()[0].replace('id', ''))
                        return f"{100 - idle:.1f}%"
        except:
            pass
        return "未知"
    
    def parse_memory_usage(self, free_output: str) -> str:
        """解析記憶體使用"""
        try:
            lines = free_output.split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 7:
                    total = parts[1]
                    used = parts[2]
                    return f"{used}/{total}"
        except:
            pass
        return "未知"
    
    def parse_load_average(self, load_output: str) -> str:
        """解析系統負載"""
        try:
            parts = load_output.strip().split()
            if len(parts) >= 3:
                return f"{parts[0]} {parts[1]} {parts[2]}"
        except:
            pass
        return "未知"
    
    def format_timestamp(self, timestamp_ms: int) -> str:
        """格式化時間戳"""
        if not timestamp_ms:
            return "未知"
        
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        now = datetime.now()
        diff = now - dt
        
        if diff < timedelta(minutes=1):
            return "剛剛"
        elif diff < timedelta(hours=1):
            return f"{int(diff.total_seconds() / 60)}分鐘前"
        elif diff < timedelta(days=1):
            return f"{int(diff.total_seconds() / 3600)}小時前"
        else:
            return f"{diff.days}天前"
    
    def get_task_status(self, session: Dict) -> str:
        """獲取任務狀態"""
        updated_at = session.get("updatedAt", 0)
        now_ms = int(time.time() * 1000)
        time_diff = now_ms - updated_at
        
        if time_diff < 60000:  # 1分鐘內
            return "running"
        elif time_diff < 300000:  # 5分鐘內
            return "pending"
        else:
            return "stopped"
    
    def generate_progress_bar(self, progress: float, length: int = 10) -> str:
        """生成進度條"""
        filled = self.config['display']['progress_bar']['filled']
        empty = self.config['display']['progress_bar']['empty']
        
        filled_length = int(progress * length / 100)
        empty_length = length - filled_length
        
        return f"{filled * filled_length}{empty * empty_length} {progress:.0f}%"
    
    def generate_compact_dashboard(self) -> str:
        """生成精簡模式儀表板"""
        sessions = self.get_subagent_sessions()
        system_info = self.get_system_info()
        
        output = []
        output.append("📊 子代理任務監控儀表板")
        output.append(self.config['display']['separator'] * self.config['display']['max_width'])
        output.append(f"⏰ 更新時間: {system_info['timestamp']}")
        output.append(f"⚡ 系統狀態: CPU {system_info['cpu']} | 記憶體 {system_info['memory']}")
        output.append(f"📈 系統負載: {system_info['load']}")
        output.append(self.config['display']['separator'] * self.config['display']['max_width'])
        
        if not sessions:
            output.append("📭 目前沒有正在執行的子代理任務")
        else:
            # 統計狀態
            status_counts = {"running": 0, "pending": 0, "stopped": 0}
            for session in sessions:
                status = self.get_task_status(session)
                status_counts[status] = status_counts.get(status, 0) + 1
            
            icons = self.config['display']['status_icons']
            output.append(f"📋 任務統計: {status_counts['running']}{icons['running']} {status_counts['pending']}{icons['pending']} {status_counts['stopped']}{icons['stopped']}")
            output.append("")
            
            # 顯示任務列表
            max_tasks = self.config['dashboard']['max_tasks']
            for i, session in enumerate(sessions[:max_tasks], 1):
                label = session.get("label", "未命名任務")
                status = self.get_task_status(session)
                status_icon = icons.get(status, "⚪")
                time_str = self.format_timestamp(session.get("updatedAt"))
                
                # 簡化顯示
                output.append(f"{i}. {label}")
                output.append(f"   └─ {status_icon} {status} · {time_str}")
                
                # 顯示會話ID前8位
                key = session.get("key", "")
                if key:
                    session_id = key.split(":")[-1][:8]
                    output.append(f"   └─ 🔗 ID: {session_id}...")
        
        output.append(self.config['display']['separator'] * self.config['display']['max_width'])
        output.append("📊 命令: /monitor - 刷新監控顯示")
        output.append("🔧 命令: /performance - 系統效能報告")
        
        return "\n".join(output)
    
    def generate_detailed_dashboard(self) -> str:
        """生成詳細模式儀表板"""
        sessions = self.get_subagent_sessions()
        system_info = self.get_system_info()
        
        output = []
        output.append("📊 任務監控儀表板 - 詳細模式")
        output.append(self.config['display']['separator'] * 50)
        output.append(f"⏰ 更新時間: {system_info['timestamp']}")
        output.append(f"⚡ CPU 使用率: {system_info['cpu']}")
        output.append(f"🧠 記憶體使用: {system_info['memory']}")
        output.append(f"📈 系統負載: {system_info['load']}")
        output.append(self.config['display']['separator'] * 50)
        
        if not sessions:
            output.append("📭 目前沒有正在執行的子代理任務")
        else:
            output.append(f"📋 總任務數量: {len(sessions)} 個")
            output.append("")
            
            icons = self.config['display']['status_icons']
            
            for i, session in enumerate(sessions, 1):
                label = session.get("label", "未命名任務")
                key = session.get("key", "")
                updated_at = session.get("updatedAt", 0)
                status = self.get_task_status(session)
                status_icon = icons.get(status, "⚪")
                time_str = self.format_timestamp(updated_at)
                
                # 計算執行時間
                if updated_at:
                    dt = datetime.fromtimestamp(updated_at / 1000)
                    now = datetime.now()
                    elapsed = now - dt
                    
                    if elapsed < timedelta(minutes=1):
                        elapsed_str = f"{elapsed.seconds}秒"
                    elif elapsed < timedelta(hours=1):
                        elapsed_str = f"{int(elapsed.seconds / 60)}分鐘"
                    else:
                        hours = elapsed.seconds // 3600
                        minutes = (elapsed.seconds % 3600) // 60
                        elapsed_str = f"{hours}小時{minutes}分鐘"
                else:
                    elapsed_str = "未知"
                
                output.append(f"{i}. {label}")
                output.append(f"   ├─ 狀態: {status_icon} {status}")
                output.append(f"   ├─ 最後活動: {time_str}")
                output.append(f"   ├─ 執行時間: {elapsed_str}")
                
                if key:
                    session_id = key.split(":")[-1]
                    output.append(f"   └─ 會話ID: {session_id}")
                
                output.append("")
        
        output.append(self.config['display']['separator'] * 50)
        output.append("📊 命令: /monitor - 切換精簡模式")
        output.append("📈 命令: /monitor chart - 圖表模式")
        
        return "\n".join(output)
    
    def generate_chart_dashboard(self) -> str:
        """生成圖表模式儀表板"""
        system_info = self.get_system_info()
        
        output = []
        output.append("📈 資源使用趨勢圖")
        output.append(self.config['display']['separator'] * 50)
        output.append(f"⏰ 更新時間: {system_info['timestamp']}")
        output.append("")
        
        # 簡單的 ASCII 圖表
        try:
            cpu_percent = float(system_info['cpu'].replace('%', ''))
        except:
            cpu_percent = 0
        
        # CPU 使用率圖表
        output.append("CPU 使用率 (%)")
        for level in range(100, 0, -10):
            if cpu_percent >= level:
                bar = "█" * 10
            else:
                filled = int((cpu_percent - (level-10)) / 10 * 10) if cpu_percent > level-10 else 0
                bar = "█" * filled + "░" * (10 - filled)
            output.append(f"{level:3d} ┤ {bar}")
        
        output.append("")
        
        # 記憶體使用圖表
        try:
            mem_parts = system_info['memory'].split('/')
            if len(mem_parts) == 2:
                used = mem_parts[0]
                total = mem_parts[1]
                output.append(f"記憶體使用: {used} / {total}")
            else:
                output.append(f"記憶體使用: {system_info['memory']}")
        except:
            output.append(f"記憶體使用: {system_info['memory']}")
        
        output.append("")
        output.append(self.config['display']['separator'] * 50)
        output.append("📊 命令: /monitor - 切換精簡模式")
        output.append("📋 命令: /monitor detail - 詳細模式")
        
        return "\n".join(output)
    
    def generate_dashboard(self, mode: str = "compact") -> str:
        """生成儀表板"""
        if mode == "compact":
            return self.generate_compact_dashboard()
        elif mode == "detailed":
            return self.generate_detailed_dashboard()
        elif mode == "chart":
            return self.generate_chart_dashboard()
        else:
            return self.generate_compact_dashboard()

def main():
    """主函數"""
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "compact"
    
    monitor = SubagentMonitor()
    dashboard = monitor.generate_dashboard(mode)
    print(dashboard)

if __name__ == "__main__":
    main()