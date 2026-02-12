#!/usr/bin/env python3
"""
簡易子代理監控腳本
顯示當前正在執行的子代理任務狀態
"""

import subprocess
import json
import time
from datetime import datetime, timedelta
import os

def get_subagent_sessions():
    """獲取子代理會話列表"""
    try:
        # 使用 OpenClaw CLI 獲取會話列表
        result = subprocess.run(
            ["openclaw", "sessions", "list", "--json", "--kinds", "subagent"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            # 嘗試使用替代方法
            return get_sessions_from_api()
    except Exception as e:
        print(f"獲取會話列表失敗: {e}")
        return {"sessions": []}

def get_sessions_from_api():
    """從 API 獲取會話列表（備用方法）"""
    try:
        # 檢查是否有會話檔案
        sessions_dir = "/root/.openclaw/sessions"
        if os.path.exists(sessions_dir):
            sessions = []
            for filename in os.listdir(sessions_dir):
                if filename.endswith(".jsonl"):
                    session_id = filename.replace(".jsonl", "")
                    sessions.append({
                        "key": f"agent:main:subagent:{session_id}",
                        "label": f"會話 {session_id[:8]}",
                        "updatedAt": int(time.time() * 1000) - 3600000  # 1小時前
                    })
            return {"sessions": sessions}
    except Exception as e:
        print(f"備用方法失敗: {e}")
    
    return {"sessions": []}

def format_timestamp(timestamp_ms):
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

def format_duration(ms):
    """格式化持續時間"""
    if not ms:
        return "未知"
    
    seconds = ms / 1000
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        return f"{int(seconds / 60)}分鐘"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小時"

def get_system_info():
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
            "cpu": parse_cpu_usage(cpu_result.stdout),
            "memory": parse_memory_usage(mem_result.stdout),
            "load": parse_load_average(load_result.stdout)
        }
    except Exception as e:
        print(f"獲取系統資訊失敗: {e}")
        return {"cpu": "未知", "memory": "未知", "load": "未知"}

def parse_cpu_usage(top_output):
    """解析 CPU 使用率"""
    try:
        for line in top_output.split('\n'):
            if '%Cpu(s):' in line:
                parts = line.split(',')
                if len(parts) >= 1:
                    idle_part = parts[3] if len(parts) > 3 else parts[-1]
                    idle = float(idle_part.split()[0].replace('id', ''))
                    return f"{100 - idle:.1f}%"
    except:
        pass
    return "未知"

def parse_memory_usage(free_output):
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

def parse_load_average(load_output):
    """解析系統負載"""
    try:
        parts = load_output.strip().split()
        if len(parts) >= 3:
            return f"{parts[0]} {parts[1]} {parts[2]}"
    except:
        pass
    return "未知"

def generate_monitor_display():
    """生成監控顯示"""
    sessions_data = get_subagent_sessions()
    system_info = get_system_info()
    
    # 過濾出子代理會話
    subagents = []
    for session in sessions_data.get("sessions", []):
        if "subagent" in session.get("key", ""):
            subagents.append(session)
    
    # 按更新時間排序（最新的在前）
    subagents.sort(key=lambda x: x.get("updatedAt", 0), reverse=True)
    
    # 生成顯示
    output = []
    output.append("📊 子代理任務監控儀表板")
    output.append("─" * 40)
    output.append(f"⏰ 更新時間: {datetime.now().strftime('%H:%M:%S')}")
    output.append(f"⚡ 系統狀態: CPU {system_info['cpu']} | 記憶體 {system_info['memory']}")
    output.append(f"📈 系統負載: {system_info['load']}")
    output.append("─" * 40)
    
    if not subagents:
        output.append("📭 目前沒有正在執行的子代理任務")
    else:
        output.append(f"📋 任務數量: {len(subagents)} 個")
        output.append("")
        
        for i, agent in enumerate(subagents[:10], 1):  # 顯示前10個
            label = agent.get("label", "未命名任務")
            key = agent.get("key", "")
            updated_at = agent.get("updatedAt", 0)
            
            # 簡單狀態判斷
            now_ms = int(time.time() * 1000)
            time_diff = now_ms - updated_at
            
            if time_diff < 60000:  # 1分鐘內
                status = "🟢 執行中"
            elif time_diff < 300000:  # 5分鐘內
                status = "🟡 閒置中"
            else:
                status = "⚪ 已停止"
            
            # 簡化顯示
            time_str = format_timestamp(updated_at)
            output.append(f"{i}. {label}")
            output.append(f"   └─ {status} · {time_str}")
            
            # 顯示會話ID前8位
            if key:
                session_id = key.split(":")[-1][:8]
                output.append(f"   └─ 🔗 ID: {session_id}...")
    
    output.append("─" * 40)
    output.append("📊 命令: /monitor - 刷新監控顯示")
    output.append("🔧 命令: /performance - 系統效能報告")
    
    return "\n".join(output)

def main():
    """主函數"""
    print(generate_monitor_display())

if __name__ == "__main__":
    main()