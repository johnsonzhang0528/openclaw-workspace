#!/usr/bin/env python3
"""
快速效能檢查腳本
顯示系統資源使用情況
"""

import subprocess
import time
from datetime import datetime

def run_command(cmd):
    """執行命令並返回輸出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"錯誤: {e}"

def get_system_info():
    """獲取系統資訊"""
    print("=" * 60)
    print("📊 系統效能監控報告")
    print("=" * 60)
    
    # 時間資訊
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"📅 報告時間: {now}")
    print()
    
    # 系統運行時間
    uptime = run_command("uptime")
    print(f"⏱️  系統運行時間: {uptime}")
    print()
    
    # CPU 使用率
    cpu_info = run_command("top -bn1 | grep 'Cpu(s)'")
    print(f"⚡ CPU 使用率: {cpu_info}")
    
    # 記憶體使用
    mem_info = run_command("free -h | grep Mem")
    if mem_info:
        parts = mem_info.split()
        total = parts[1]
        used = parts[2]
        free = parts[3]
        available = parts[6]
        print(f"🧠 記憶體: 總 {total} | 已用 {used} | 可用 {free} | 可用 {available}")
    
    # 磁碟使用
    disk_info = run_command("df -h / | tail -1")
    if disk_info:
        parts = disk_info.split()
        filesystem = parts[0]
        total = parts[1]
        used = parts[2]
        avail = parts[3]
        use_percent = parts[4]
        print(f"💾 磁碟 (/): {filesystem} | 總 {total} | 已用 {used} | 可用 {avail} | 使用率 {use_percent}")
    
    print()
    
    # 負載平均
    load_avg = run_command("cat /proc/loadavg")
    if load_avg:
        loads = load_avg.split()[:3]
        print(f"📈 系統負載 (1/5/15分鐘): {loads[0]}/{loads[1]}/{loads[2]}")
    
    # 進程數量
    process_count = run_command("ps aux | wc -l")
    print(f"🔢 總進程數: {process_count}")
    
    print()
    
    # OpenClaw 相關進程
    print("🤖 OpenClaw 相關進程:")
    openclaw_procs = run_command("ps aux | grep -E '(openclaw|node)' | grep -v grep | head -5")
    if openclaw_procs:
        for line in openclaw_procs.split('\n'):
            if line.strip():
                parts = line.split()
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                cmd = ' '.join(parts[10:])[:50]
                print(f"  PID {pid}: CPU {cpu}% | MEM {mem}% | {cmd}")
    else:
        print("  未找到 OpenClaw 進程")
    
    print()
    
    # 網路連接
    net_conn = run_command("ss -tun | wc -l")
    print(f"🌐 網路連接數: {int(net_conn) - 1}")
    
    # 溫度（如果可用）
    temp_info = run_command("cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1")
    if temp_info and temp_info.isdigit():
        temp_c = int(temp_info) / 1000
        print(f"🌡️  CPU 溫度: {temp_c:.1f}°C")
    
    print("=" * 60)
    print("💡 建議:")
    
    # 提供建議
    mem_avail = run_command("free -m | grep Mem | awk '{print $7}'")
    if mem_avail and mem_avail.isdigit():
        avail_mb = int(mem_avail)
        if avail_mb < 500:
            print("⚠️  可用記憶體偏低 (<500MB)")
        elif avail_mb < 1000:
            print("ℹ️  可用記憶體中等")
        else:
            print("✅ 記憶體充足")
    
    disk_use = run_command("df / | tail -1 | awk '{print $5}' | sed 's/%//'")
    if disk_use and disk_use.isdigit():
        use_percent = int(disk_use)
        if use_percent > 90:
            print("⚠️  磁碟使用率過高 (>90%)")
        elif use_percent > 80:
            print("ℹ️  磁碟使用率偏高 (>80%)")
        else:
            print("✅ 磁碟空間充足")
    
    print("=" * 60)

if __name__ == "__main__":
    get_system_info()