#!/usr/bin/env python3
"""
修復版監控儀表板 - 正確計算子代理會話數量
"""

import json
import subprocess
import time
from datetime import datetime, timedelta
import os
import sys

def get_all_sessions():
    """獲取所有會話數據"""
    try:
        cmd = ["openclaw", "sessions", "list", "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ 執行 openclaw 命令失敗: {result.stderr}")
            return {"sessions": []}
        
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析錯誤: {e}")
            return {"sessions": []}
                
    except subprocess.TimeoutExpired:
        print("❌ 命令執行超時")
        return {"sessions": []}
    except Exception as e:
        print(f"❌ 獲取會話數據時發生錯誤: {e}")
        return {"sessions": []}

def is_subagent_session(session_key):
    """判斷是否為子代理會話"""
    if not session_key:
        return False
    
    # 子代理會話的 key 通常包含以下模式
    subagent_patterns = [
        ":subagent:",  # 子代理會話
        ":cron:",      # cron 任務會話
        "agent:main:subagent",  # 子代理會話
        "agent:main:cron"       # cron 會話
    ]
    
    for pattern in subagent_patterns:
        if pattern in session_key:
            return True
    
    return False

def analyze_sessions_correctly(sessions_data):
    """正確分析會話數據，區分主會話和子代理會話"""
    sessions = sessions_data.get("sessions", [])
    
    # 分類會話
    all_sessions = []
    subagent_sessions = []
    main_sessions = []
    
    now = datetime.now()
    
    for session in sessions:
        key = session.get("key", "")
        updated_at = session.get("updatedAt")
        
        if not key:
            continue
            
        session_info = {
            "key": key,
            "kind": session.get("kind", ""),
            "model": session.get("model", ""),
            "is_subagent": is_subagent_session(key)
        }
        
        # 計算會話年齡
        if updated_at:
            try:
                timestamp = updated_at / 1000  # 毫秒轉秒
                session_time = datetime.fromtimestamp(timestamp)
                age = now - session_time
                session_info["age_minutes"] = int(age.total_seconds() / 60)
                session_info["age_seconds"] = int(age.total_seconds())
            except:
                session_info["age_minutes"] = 999
                session_info["age_seconds"] = 99999
        
        all_sessions.append(session_info)
        
        if session_info["is_subagent"]:
            subagent_sessions.append(session_info)
        else:
            main_sessions.append(session_info)
    
    # 進一步分類子代理會話
    active_subagents = []
    recent_subagents = []
    old_subagents = []
    
    for session in subagent_sessions:
        age_seconds = session.get("age_seconds", 99999)
        
        if age_seconds < 300:  # 5分鐘內
            active_subagents.append(session)
        elif age_seconds < 3600:  # 1小時內
            recent_subagents.append(session)
        else:
            old_subagents.append(session)
    
    return {
        # 總計數
        "total_all": len(all_sessions),
        "total_subagents": len(subagent_sessions),
        "total_main": len(main_sessions),
        
        # 子代理會話分類
        "subagents_active": len(active_subagents),
        "subagents_recent": len(recent_subagents),
        "subagents_old": len(old_subagents),
        
        # 詳細列表
        "active_subagents": active_subagents,
        "recent_subagents": recent_subagents,
        "old_subagents": old_subagents,
        
        # 主會話
        "main_sessions": main_sessions
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

def generate_fixed_dashboard(session_analysis, system_metrics):
    """生成修復版儀表板"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    dashboard = f"""🔧 **修復版監控儀表板** ({now})

📊 **會話統計（正確計算）**
├ 總會話數: {session_analysis['total_all']}
├ 主會話數: {session_analysis['total_main']}
└ **子代理會話: {session_analysis['total_subagents']}**

🤖 **子代理任務狀態**
├ 活躍中 (<5m): {session_analysis['subagents_active']}
├ 近期內 (<1h): {session_analysis['subagents_recent']}
└ 歷史會話: {session_analysis['subagents_old']}

⚙️ **系統資源**
├ CPU: {system_metrics['cpu_percent']:.1f}%
├ 記憶體: {system_metrics['memory_percent']:.1f}%
├ 磁碟: {system_metrics['disk_percent']:.1f}%
└ 負載: {system_metrics['load_avg'][0]:.2f} {system_metrics['load_avg'][1]:.2f} {system_metrics['load_avg'][2]:.2f}

🔄 **活躍子代理任務**
"""
    
    if session_analysis['active_subagents']:
        for i, session in enumerate(session_analysis['active_subagents'][:5], 1):
            # 提取會話 ID
            key_parts = session['key'].split(':')
            session_id = key_parts[-1][:8] if len(key_parts) > 0 else session['key'][:8]
            dashboard += f"├ {i}. {session_id} ({session.get('age_minutes', '?')}m) - {session['model']}\n"
        if len(session_analysis['active_subagents']) > 5:
            dashboard += f"└ ... 還有 {len(session_analysis['active_subagents']) - 5} 個任務\n"
    else:
        dashboard += "└ 目前沒有活躍的子代理任務\n"
    
    # 添加診斷資訊
    dashboard += f"\n🔍 **診斷資訊**\n"
    dashboard += f"├ 之前錯誤計數: 22-25 (包含所有會話)\n"
    dashboard += f"├ 正確計數: {session_analysis['total_subagents']} (僅子代理會話)\n"
    dashboard += f"└ 警報閾值: 20 (僅適用於子代理會話)\n"
    
    return dashboard

def update_monitoring_state_correctly(session_analysis, system_metrics):
    """更新監控狀態檔案（使用正確的計數）"""
    state_file = "/root/.openclaw/workspace/monitoring-state.json"
    
    try:
        # 讀取現有狀態
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
        else:
            state = {}
        
        # 更新狀態
        now = datetime.now().isoformat()
        state["last_update"] = now
        
        # 使用正確的任務統計
        state["tasks"] = {
            "total": session_analysis["total_subagents"],  # 僅子代理會話
            "running": session_analysis["subagents_active"],
            "completed": session_analysis["subagents_old"],
            "failed": 0,
            "pending": session_analysis["subagents_recent"]
        }
        
        # 更新系統指標
        state["system_metrics"] = {
            "cpu_load": system_metrics["cpu_percent"],
            "memory_percent": system_metrics["memory_percent"],
            "disk_percent": system_metrics["disk_percent"],
            "load_average": system_metrics["load_avg"]
        }
        
        # 添加診斷資訊
        state["diagnostics"] = {
            "total_sessions_all": session_analysis["total_all"],
            "total_sessions_main": session_analysis["total_main"],
            "total_sessions_subagents": session_analysis["total_subagents"],
            "calculation_fixed": True,
            "fixed_at": now,
            "previous_error": "counted_all_sessions_instead_of_subagents_only"
        }
        
        # 寫入檔案
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 監控狀態已更新（使用正確計數）: {state_file}")
        return True
        
    except Exception as e:
        print(f"❌ 更新監控狀態時出錯: {e}")
        return False

def main():
    """主函數"""
    print("🔧 啟動修復版監控儀表板...")
    
    # 獲取所有會話數據
    print("📡 獲取所有會話數據...")
    sessions_data = get_all_sessions()
    
    # 正確分析會話
    print("🔍 正確分析會話數據（區分主會話和子代理會話）...")
    session_analysis = analyze_sessions_correctly(sessions_data)
    
    # 獲取系統指標
    print("⚙️  獲取系統指標...")
    system_metrics = get_system_metrics()
    
    # 生成儀表板
    print("📊 生成修復版監控儀表板...")
    dashboard = generate_fixed_dashboard(session_analysis, system_metrics)
    
    # 顯示儀表板
    print("\n" + "="*60)
    print(dashboard)
    print("="*60)
    
    # 更新監控狀態（使用正確計數）
    print("\n💾 更新監控狀態檔案（使用正確計數）...")
    update_monitoring_state_correctly(session_analysis, system_metrics)
    
    # 保存儀表板到檔案
    dashboard_file = "/root/.openclaw/workspace/latest_dashboard_fixed.txt"
    with open(dashboard_file, 'w') as f:
        f.write(dashboard)
    
    print(f"✅ 修復版儀表板已保存: {dashboard_file}")
    
    # 顯示關鍵資訊
    print(f"\n📋 **關鍵修復結果**:")
    print(f"├ 總會話數: {session_analysis['total_all']}")
    print(f"├ 主會話數: {session_analysis['total_main']}")
    print(f"├ 子代理會話: {session_analysis['total_subagents']} ✅")
    print(f"└ 是否超過閾值(20): {session_analysis['total_subagents'] > 20}")
    
    return dashboard

if __name__ == "__main__":
    dashboard_text = main()
    
    # 輸出結果供外部使用
    print("\n📋 修復版儀表板內容:")
    print("-"*40)
    print(dashboard_text)
    print("-"*40)