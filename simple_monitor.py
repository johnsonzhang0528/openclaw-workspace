#!/usr/bin/env python3
"""
簡易監控指令處理器
用於 Telegram 的 /monitor 指令
"""

import subprocess
import json
import time
from datetime import datetime, timedelta
import os

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
        
        # 磁碟使用
        disk_result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return {
            "cpu": parse_cpu_usage(cpu_result.stdout),
            "memory": parse_memory_usage(mem_result.stdout),
            "load": parse_load_average(load_result.stdout),
            "disk": parse_disk_usage(disk_result.stdout)
        }
    except Exception as e:
        return {"cpu": "未知", "memory": "未知", "load": "未知", "disk": "未知"}

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
                percent = parts[4].replace('%', '')
                return f"{used}/{total} ({percent}%)"
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

def parse_disk_usage(df_output):
    """解析磁碟使用"""
    try:
        lines = df_output.split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                used = parts[2]
                total = parts[1]
                percent = parts[4]
                return f"{used}/{total} ({percent})"
    except:
        pass
    return "未知"

def get_subagent_tasks():
    """獲取子代理任務"""
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
            tasks = []
            
            for session in data.get("sessions", []):
                if "subagent" in session.get("key", ""):
                    task = {
                        "label": session.get("label", "未命名任務"),
                        "key": session.get("key", ""),
                        "updatedAt": session.get("updatedAt", 0),
                        "status": "unknown"
                    }
                    
                    # 判斷狀態
                    now_ms = int(time.time() * 1000)
                    time_diff = now_ms - task["updatedAt"]
                    
                    if time_diff < 60000:  # 1分鐘內
                        task["status"] = "running"
                    elif time_diff < 300000:  # 5分鐘內
                        task["status"] = "idle"
                    else:
                        task["status"] = "stopped"
                    
                    tasks.append(task)
            
            return tasks
    except Exception as e:
        print(f"獲取子代理任務失敗: {e}")
    
    return []

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

def generate_monitor_message():
    """生成監控訊息"""
    system_info = get_system_info()
    tasks = get_subagent_tasks()
    
    # 計算任務統計
    running_tasks = len([t for t in tasks if t["status"] == "running"])
    idle_tasks = len([t for t in tasks if t["status"] == "idle"])
    stopped_tasks = len([t for t in tasks if t["status"] == "stopped"])
    
    # 建立訊息
    message = []
    message.append("📊 *即時系統監控儀表板*")
    message.append("")
    message.append("*系統狀態*")
    message.append(f"⚡ CPU: `{system_info['cpu']}`")
    message.append(f"🧠 記憶體: `{system_info['memory']}`")
    message.append(f"💾 磁碟: `{system_info['disk']}`")
    message.append(f"📈 負載: `{system_info['load']}`")
    message.append("")
    message.append("*子代理任務*")
    message.append(f"🟢 執行中: `{running_tasks}`")
    message.append(f"🟡 閒置中: `{idle_tasks}`")
    message.append(f"⚪ 已停止: `{stopped_tasks}`")
    message.append(f"📋 總數: `{len(tasks)}`")
    
    if tasks:
        message.append("")
        message.append("*最近任務*")
        
        # 顯示前5個任務
        for i, task in enumerate(tasks[:5], 1):
            status_emoji = {
                "running": "🟢",
                "idle": "🟡",
                "stopped": "⚪"
            }.get(task["status"], "❓")
            
            label = task["label"][:30] + "..." if len(task["label"]) > 30 else task["label"]
            time_str = format_timestamp(task["updatedAt"])
            
            message.append(f"{i}. {status_emoji} `{label}`")
            message.append(f"   └─ {time_str}")
    
    message.append("")
    message.append("⏰ *更新時間*: " + datetime.now().strftime("%H:%M:%S"))
    message.append("")
    message.append("📊 使用 `/monitor` 刷新")
    message.append("⚡ 使用 `/performance` 查看詳細效能")
    
    return "\n".join(message)

def main():
    """主函數"""
    print(generate_monitor_message())

if __name__ == "__main__":
    main()