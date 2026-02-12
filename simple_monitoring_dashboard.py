#!/usr/bin/env python3
"""
簡化監控儀表板 - 解決 JSON 解析錯誤問題
"""

import json
import subprocess
import time
from datetime import datetime, timedelta
import os
import sys

def get_sessions_data():
    """獲取會話數據，處理 JSON 解析錯誤"""
    try:
        # 使用 subprocess 獲取會話列表
        cmd = ["openclaw", "sessions", "list", "--json", "--kinds", "subagent"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ 執行 openclaw 命令失敗: {result.stderr}")
            return {"sessions": []}
        
        # 處理可能的 JSON 解析錯誤
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析錯誤: {e}")
            print(f"原始輸出前 500 字元: {result.stdout[:500]}")
            
            # 嘗試修復 JSON
            fixed_json = fix_json(result.stdout)
            try:
                data = json.loads(fixed_json)
                print("✅ JSON 修復成功")
                return data
            except:
                print("❌ JSON 修復失敗，返回空數據")
                return {"sessions": []}
                
    except subprocess.TimeoutExpired:
        print("❌ 命令執行超時")
        return {"sessions": []}
    except Exception as e:
        print(f"❌ 獲取會話數據時發生錯誤: {e}")
        return {"sessions": []}

def fix_json(json_str):
    """嘗試修復 JSON 字符串"""
    # 移除可能的控制字符
    json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in '\n\r\t')
    
    # 修復未終止的字符串
    lines = json_str.split('\n')
    fixed_lines = []
    in_string = False
    escape_next = False
    
    for line in lines:
        fixed_line = ''
        for char in line:
            if escape_next:
                fixed_line += char
                escape_next = False
            elif char == '\\':
                fixed_line += char
                escape_next = True
            elif char == '"':
                fixed_line += char
                in_string = not in_string
            else:
                fixed_line += char
        
        # 如果字符串未終止，添加終止符
        if in_string:
            fixed_line += '"'
            in_string = False
        
        fixed_lines.append(fixed_line)
    
    return '\n'.join(fixed_lines)

def analyze_sessions(sessions_data):
    """分析會話數據"""
    sessions = sessions_data.get("sessions", [])
    
    # 分類會話
    active_sessions = []
    recent_sessions = []
    old_sessions = []
    
    now = datetime.now()
    
    for session in sessions:
        updated_at = session.get("updatedAt")
        if updated_at:
            # 轉換時間戳
            try:
                timestamp = updated_at / 1000  # 毫秒轉秒
                session_time = datetime.fromtimestamp(timestamp)
                age = now - session_time
                
                session_info = {
                    "key": session.get("key", ""),
                    "age_minutes": int(age.total_seconds() / 60),
                    "kind": session.get("kind", ""),
                    "model": session.get("model", ""),
                    "context_tokens": session.get("contextTokens", 0)
                }
                
                # 分類
                if age.total_seconds() < 300:  # 5分鐘內
                    active_sessions.append(session_info)
                elif age.total_seconds() < 3600:  # 1小時內
                    recent_sessions.append(session_info)
                else:
                    old_sessions.append(session_info)
                    
            except Exception as e:
                print(f"⚠️  處理會話時間時出錯: {e}")
    
    return {
        "total": len(sessions),
        "active": len(active_sessions),
        "recent": len(recent_sessions),
        "old": len(old_sessions),
        "active_sessions": active_sessions,
        "recent_sessions": recent_sessions,
        "old_sessions": old_sessions
    }

def get_system_metrics():
    """獲取系統指標"""
    try:
        # CPU 使用率
        cpu_cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
        cpu_result = subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True)
        cpu_percent = float(cpu_result.stdout.strip()) if cpu_result.stdout.strip() else 0
        
        # 記憶體使用率
        mem_cmd = "free | grep Mem | awk '{print $3/$2 * 100.0}'"
        mem_result = subprocess.run(mem_cmd, shell=True, capture_output=True, text=True)
        mem_percent = float(mem_result.stdout.strip()) if mem_result.stdout.strip() else 0
        
        # 磁碟使用率
        disk_cmd = "df -h / | tail -1 | awk '{print $5}' | sed 's/%//'"
        disk_result = subprocess.run(disk_cmd, shell=True, capture_output=True, text=True)
        disk_percent = float(disk_result.stdout.strip()) if disk_result.stdout.strip() else 0
        
        # 負載平均值
        load_cmd = "uptime | awk -F'load average:' '{print $2}' | awk '{print $1,$2,$3}'"
        load_result = subprocess.run(load_cmd, shell=True, capture_output=True, text=True)
        load_output = load_result.stdout.strip()
        if load_output:
            load_parts = load_output.split()
            load_avg = [float(x.strip(',')) for x in load_parts[:3]]
        else:
            load_avg = [0, 0, 0]
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": mem_percent,
            "disk_percent": disk_percent,
            "load_avg": load_avg
        }
        
    except Exception as e:
        print(f"❌ 獲取系統指標時出錯: {e}")
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "load_avg": [0, 0, 0]
        }

def generate_compact_dashboard(session_analysis, system_metrics):
    """生成精簡儀表板"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    dashboard = f"""📊 **OpenClaw 監控儀表板** ({now})

🤖 **子代理任務狀態**
├ 總會話數: {session_analysis['total']}
├ 活躍中 (<5m): {session_analysis['active']}
├ 近期內 (<1h): {session_analysis['recent']}
└ 歷史會話: {session_analysis['old']}

⚙️ **系統資源**
├ CPU: {system_metrics['cpu_percent']:.1f}%
├ 記憶體: {system_metrics['memory_percent']:.1f}%
├ 磁碟: {system_metrics['disk_percent']:.1f}%
└ 負載: {system_metrics['load_avg'][0]:.2f} {system_metrics['load_avg'][1]:.2f} {system_metrics['load_avg'][2]:.2f}

🔄 **活躍任務**
"""
    
    if session_analysis['active_sessions']:
        for i, session in enumerate(session_analysis['active_sessions'][:5], 1):
            key_short = session['key'].split(':')[-1][:8] if ':' in session['key'] else session['key'][:8]
            dashboard += f"├ {i}. {key_short} ({session['age_minutes']}m) - {session['model']}\n"
        if len(session_analysis['active_sessions']) > 5:
            dashboard += f"└ ... 還有 {len(session_analysis['active_sessions']) - 5} 個任務\n"
    else:
        dashboard += "└ 目前沒有活躍任務\n"
    
    return dashboard

def update_monitoring_state(session_analysis, system_metrics):
    """更新監控狀態檔案"""
    state_file = "/root/.openclaw/workspace/monitoring-state.json"
    
    try:
        # 讀取現有狀態
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
        else:
            state = {
                "version": "1.0",
                "last_update": "",
                "monitoring_enabled": True,
                "tasks": {},
                "current_tasks": [],
                "completed_tasks": [],
                "system_metrics": {},
                "monitoring_config": {},
                "alerts": {},
                "performance_stats": {}
            }
        
        # 更新狀態
        now = datetime.now().isoformat()
        state["last_update"] = now
        
        # 更新任務統計
        state["tasks"] = {
            "total": session_analysis["total"],
            "running": session_analysis["active"],
            "completed": session_analysis["old"],  # 歷史會話視為完成
            "failed": 0,
            "pending": session_analysis["recent"]  # 近期會話視為待處理
        }
        
        # 更新系統指標
        state["system_metrics"] = {
            "cpu_load": system_metrics["cpu_percent"],
            "memory_used_gb": 0,  # 需要額外計算
            "memory_total_gb": 0,
            "memory_percent": system_metrics["memory_percent"],
            "disk_used_gb": 0,
            "disk_total_gb": 0,
            "disk_percent": system_metrics["disk_percent"],
            "uptime_days": 1,
            "uptime_hours": 14,
            "load_average": system_metrics["load_avg"]
        }
        
        # 寫入檔案
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 監控狀態已更新: {state_file}")
        return True
        
    except Exception as e:
        print(f"❌ 更新監控狀態時出錯: {e}")
        return False

def main():
    """主函數"""
    print("🚀 啟動簡化監控儀表板...")
    
    # 獲取會話數據
    print("📡 獲取會話數據...")
    sessions_data = get_sessions_data()
    
    # 分析會話
    print("🔍 分析會話數據...")
    session_analysis = analyze_sessions(sessions_data)
    
    # 獲取系統指標
    print("⚙️  獲取系統指標...")
    system_metrics = get_system_metrics()
    
    # 生成儀表板
    print("📊 生成監控儀表板...")
    dashboard = generate_compact_dashboard(session_analysis, system_metrics)
    
    # 顯示儀表板
    print("\n" + "="*60)
    print(dashboard)
    print("="*60)
    
    # 更新監控狀態
    print("\n💾 更新監控狀態檔案...")
    update_monitoring_state(session_analysis, system_metrics)
    
    # 保存儀表板到檔案
    dashboard_file = "/root/.openclaw/workspace/latest_dashboard.txt"
    with open(dashboard_file, 'w') as f:
        f.write(dashboard)
    
    print(f"✅ 儀表板已保存: {dashboard_file}")
    
    return dashboard

if __name__ == "__main__":
    dashboard_text = main()
    
    # 輸出結果供外部使用
    print("\n📋 儀表板內容（供 Telegram 發送）:")
    print("-"*40)
    print(dashboard_text)
    print("-"*40)