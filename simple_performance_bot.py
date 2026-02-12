#!/usr/bin/env python3
"""
簡單效能監控 Telegram 機器人
無需安裝 psutil，使用系統命令
"""

import subprocess
import time
from datetime import datetime
import json
from typing import Dict, List, Optional

def run_command(cmd: str) -> str:
    """執行命令並返回輸出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"錯誤: {e}"

def get_system_info() -> Dict[str, any]:
    """獲取系統資訊"""
    info = {}
    
    # 時間
    info['timestamp'] = datetime.now().isoformat()
    
    # 運行時間
    uptime = run_command("uptime")
    info['uptime'] = uptime
    
    # CPU 資訊
    cpu_line = run_command("top -bn1 | grep 'Cpu(s)'")
    info['cpu'] = cpu_line
    
    # 記憶體資訊
    mem_line = run_command("free -h | grep Mem")
    if mem_line:
        parts = mem_line.split()
        info['memory'] = {
            'total': parts[1],
            'used': parts[2],
            'free': parts[3],
            'available': parts[6]
        }
    
    # 磁碟資訊
    disk_line = run_command("df -h / | tail -1")
    if disk_line:
        parts = disk_line.split()
        info['disk'] = {
            'filesystem': parts[0],
            'total': parts[1],
            'used': parts[2],
            'available': parts[3],
            'use_percent': parts[4]
        }
    
    # 負載平均
    load_avg = run_command("cat /proc/loadavg")
    if load_avg:
        loads = load_avg.split()[:3]
        info['load_avg'] = {
            '1min': loads[0],
            '5min': loads[1],
            '15min': loads[2]
        }
    
    # 進程數量
    process_count = run_command("ps aux | wc -l")
    info['process_count'] = process_count
    
    # 網路連接
    net_conn = run_command("ss -tun | wc -l")
    info['network_connections'] = int(net_conn) - 1 if net_conn.isdigit() else 0
    
    return info

def format_system_info(info: Dict) -> str:
    """格式化系統資訊為 Telegram 訊息"""
    lines = []
    
    lines.append("📊 **即時系統效能報告**")
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 運行時間
    if 'uptime' in info:
        lines.append(f"⏱️  {info['uptime']}")
        lines.append("")
    
    # CPU
    if 'cpu' in info:
        # 解析 CPU 使用率
        cpu_text = info['cpu']
        if '%Cpu(s):' in cpu_text:
            # 提取數字
            import re
            cpu_parts = re.findall(r'[\d.]+', cpu_text)
            if len(cpu_parts) >= 4:
                us, sy, ni, id = cpu_parts[:4]
                cpu_used = 100 - float(id)
                lines.append(f"⚡ **CPU**: {cpu_used:.1f}% 使用")
                lines.append(f"  (用戶: {us}%, 系統: {sy}%, 空閒: {id}%)")
    
    # 記憶體
    if 'memory' in info:
        mem = info['memory']
        lines.append(f"🧠 **記憶體**: {mem['used']}/{mem['total']} 使用")
        lines.append(f"  (可用: {mem['available']}, 空閒: {mem['free']})")
    
    # 磁碟
    if 'disk' in info:
        disk = info['disk']
        lines.append(f"💾 **磁碟**: {disk['use_percent']} 使用")
        lines.append(f"  ({disk['used']}/{disk['total']}, 可用: {disk['available']})")
    
    # 負載
    if 'load_avg' in info:
        load = info['load_avg']
        lines.append(f"📈 **系統負載**: {load['1min']} ({load['5min']}/{load['15min']})")
    
    # 進程和連接
    lines.append(f"🔢 **進程數**: {info.get('process_count', 'N/A')}")
    lines.append(f"🌐 **網路連接**: {info.get('network_connections', 0)}")
    
    lines.append("")
    lines.append("💡 **狀態評估**:")
    
    # 評估系統狀態
    warnings = []
    
    # 檢查記憶體
    if 'memory' in info:
        mem = info['memory']
        # 解析可用記憶體
        if 'Gi' in mem['available']:
            avail_gb = float(mem['available'].replace('Gi', ''))
            if avail_gb < 0.5:
                warnings.append("⚠️ 可用記憶體偏低 (<500MB)")
            elif avail_gb < 1.0:
                warnings.append("ℹ️ 可用記憶體中等")
    
    # 檢查磁碟
    if 'disk' in info:
        disk = info['disk']
        use_percent = int(disk['use_percent'].replace('%', ''))
        if use_percent > 90:
            warnings.append("⚠️ 磁碟使用率過高 (>90%)")
        elif use_percent > 80:
            warnings.append("ℹ️ 磁碟使用率偏高 (>80%)")
    
    if warnings:
        for warning in warnings:
            lines.append(warning)
    else:
        lines.append("✅ 系統狀態良好")
    
    return "\n".join(lines)

def get_top_processes(count: int = 5) -> List[Dict]:
    """獲取資源消耗最多的進程"""
    processes = []
    
    # 使用 top 命令獲取進程資訊
    top_output = run_command(f"top -bn1 -o %CPU | head -{count + 7}")
    lines = top_output.split('\n')
    
    # 跳過標頭行
    for line in lines[7:7+count]:
        if line.strip():
            parts = line.split()
            if len(parts) >= 12:
                pid = parts[0]
                user = parts[1]
                cpu = parts[8]
                mem = parts[9]
                command = ' '.join(parts[11:])[:30]
                
                processes.append({
                    'pid': pid,
                    'user': user,
                    'cpu': cpu,
                    'mem': mem,
                    'command': command
                })
    
    return processes

def format_top_processes(processes: List[Dict]) -> str:
    """格式化進程列表"""
    if not processes:
        return "🔍 未找到進程資訊"
    
    lines = []
    lines.append("🔥 **資源消耗最多的進程**")
    lines.append("")
    
    for i, proc in enumerate(processes, 1):
        cpu = float(proc['cpu'])
        mem = float(proc['mem'])
        
        # 根據 CPU 使用率添加圖示
        if cpu > 50:
            icon = "🔥"
        elif cpu > 20:
            icon = "⚡"
        elif cpu > 5:
            icon = "📈"
        else:
            icon = "📊"
        
        lines.append(f"{icon} **{i}. {proc['command']}**")
        lines.append(f"   PID: {proc['pid']} | CPU: {cpu}% | 記憶體: {mem}%")
    
    return "\n".join(lines)

def get_system_stats() -> str:
    """獲取系統統計資訊"""
    info = get_system_info()
    
    lines = []
    lines.append("📋 **系統詳細統計**")
    lines.append("")
    
    # CPU 核心數
    cpu_count = run_command("nproc")
    lines.append(f"🖥️  **CPU 核心數**: {cpu_count}")
    
    # 記憶體總量
    if 'memory' in info:
        lines.append(f"🧠 **總記憶體**: {info['memory']['total']}")
    
    # 磁碟總量
    if 'disk' in info:
        lines.append(f"💾 **總磁碟空間**: {info['disk']['total']}")
    
    # 系統架構
    arch = run_command("uname -m")
    lines.append(f"🏗️  **系統架構**: {arch}")
    
    # 作業系統
    os_info = run_command("cat /etc/os-release | grep PRETTY_NAME")
    if os_info:
        os_name = os_info.split('=')[1].strip('"')
        lines.append(f"🐧 **作業系統**: {os_name}")
    
    # 核心版本
    kernel = run_command("uname -r")
    lines.append(f"🔧 **核心版本**: {kernel}")
    
    lines.append("")
    lines.append("📊 **效能指標**:")
    
    # 解析負載
    if 'load_avg' in info:
        load = info['load_avg']
        load_1 = float(load['1min'])
        cpu_cores = int(cpu_count)
        load_per_core = load_1 / cpu_cores if cpu_cores > 0 else 0
        
        lines.append(f"  📈 每核心負載: {load_per_core:.2f}")
        
        if load_per_core > 2:
            lines.append("  ⚠️  系統過載")
        elif load_per_core > 1:
            lines.append("  ℹ️  負載偏高")
        else:
            lines.append("  ✅ 負載正常")
    
    return "\n".join(lines)

def handle_command(command: str) -> str:
    """處理命令"""
    cmd = command.lower().strip().lstrip('/')
    
    if cmd in ["performance", "perf", "sysinfo"]:
        info = get_system_info()
        return format_system_info(info)
    
    elif cmd in ["processes", "top", "procs"]:
        processes = get_top_processes(6)
        return format_top_processes(processes)
    
    elif cmd in ["stats", "statistics", "details"]:
        return get_system_stats()
    
    elif cmd in ["help", "?"]:
        return get_help()
    
    else:
        return f"❓ 未知命令: {command}\n\n{get_help()}"

def get_help() -> str:
    """獲取幫助訊息"""
    lines = []
    lines.append("🤖 **效能監控幫助**")
    lines.append("")
    lines.append("**可用命令:**")
    lines.append("`/performance` - 顯示系統效能")
    lines.append("`/processes` - 顯示熱門進程")
    lines.append("`/stats` - 顯示詳細統計")
    lines.append("`/help` - 顯示此幫助")
    lines.append("")
    lines.append("**別名:**")
    lines.append("`/perf`, `/sysinfo` = `/performance`")
    lines.append("`/top`, `/procs` = `/processes`")
    lines.append("`/statistics`, `/details` = `/stats`")
    lines.append("")
    lines.append("**數據來源:** 系統命令 (top, free, df, uptime)")
    lines.append("**更新:** 實時數據")
    
    return "\n".join(lines)

def get_inline_buttons() -> List[List[Dict]]:
    """獲取 inline 按鈕配置"""
    return [
        [
            {"text": "📊 系統效能", "callback_data": "cmd_performance"},
            {"text": "🔥 熱門進程", "callback_data": "cmd_processes"}
        ],
        [
            {"text": "📋 詳細統計", "callback_data": "cmd_stats"},
            {"text": "🔄 刷新", "callback_data": "cmd_refresh"}
        ],
        [
            {"text": "❓ 幫助", "callback_data": "cmd_help"}
        ]
    ]

def test_all_commands():
    """測試所有命令"""
    commands = [
        "/performance",
        "/processes",
        "/stats",
        "/help"
    ]
    
    for cmd in commands:
        print(f"\n{'='*60}")
        print(f"測試命令: {cmd}")
        print(f"{'='*60}")
        result = handle_command(cmd)
        print(result)
        print()
        time.sleep(1)

if __name__ == "__main__":
    print("🔧 簡單效能監控機器人測試")
    print("=" * 60)
    test_all_commands()
    
    # 顯示 inline 按鈕配置
    print("\n📱 Inline 按鈕配置:")
    buttons = get_inline_buttons()
    print(json.dumps(buttons, indent=2, ensure_ascii=False))