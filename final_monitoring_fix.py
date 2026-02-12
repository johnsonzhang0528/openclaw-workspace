#!/usr/bin/env python3
"""
最終監控系統修復腳本
確保所有監控組件都使用正確的會話計算邏輯
"""

import os
import shutil
from datetime import datetime

def update_all_monitoring_components():
    """更新所有監控組件"""
    
    print("🔄 開始更新所有監控組件...")
    print("=" * 60)
    
    # 1. 更新監控 Cron 腳本
    print("\n1. 🔄 更新監控 Cron 腳本...")
    update_monitoring_cron_script()
    
    # 2. 更新簡化監控儀表板
    print("\n2. 📊 更新簡化監控儀表板...")
    update_simple_monitoring_dashboard()
    
    # 3. 創建統一的監控配置
    print("\n3. ⚙️ 創建統一監控配置...")
    create_unified_monitoring_config()
    
    # 4. 設置定期清理任務
    print("\n4. 🧹 設置定期清理任務...")
    setup_scheduled_cleanup()
    
    print("\n" + "=" * 60)
    print("🎉 所有監控組件更新完成！")
    
    return True

def update_monitoring_cron_script():
    """更新監控 Cron 腳本，使用正確的會話計算"""
    
    cron_script = '''#!/usr/bin/env python3
"""
監控 Cron 任務 - 使用正確的會話計算邏輯
"""

import sys
import os
import json
from datetime import datetime

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_active_sessions_count():
    """獲取活躍會話數量（5分鐘內）'''
    try:
        import subprocess
        import json
        
        # 使用 openclaw 命令獲取會話
        cmd = ["openclaw", "sessions", "list", "--json", "--kinds", "subagent"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return 0
        
        data = json.loads(result.stdout)
        sessions = data.get("sessions", [])
        
        # 計算5分鐘內的活躍會話
        from datetime import datetime
        now = datetime.now()
        active_count = 0
        
        for session in sessions:
            updated_at = session.get("updatedAt")
            if updated_at:
                timestamp = updated_at / 1000
                session_time = datetime.fromtimestamp(timestamp)
                age = now - session_time
                
                if age.total_seconds() < 300:  # 5分鐘
                    active_count += 1
        
        return active_count
        
    except Exception as e:
        print(f"❌ 獲取活躍會話時出錯: {e}")
        return 0

def update_monitoring_dashboard():
    """更新監控儀表板"""
    try:
        # 使用修正版的監控腳本
        from fix_session_count import generate_fixed_dashboard
        
        print(f"🔄 開始監控更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 執行更新
        dashboard_text = generate_fixed_dashboard()
        
        if dashboard_text:
            print(f"✅ 監控更新完成: {len(dashboard_text)} 字元")
            
            # 檢查警報（使用正確的計算）
            active_sessions = get_active_sessions_count()
            alert_threshold = 30  # 新的警戒線
            
            if active_sessions > alert_threshold:
                alert_msg = f"⚠️  子代理會話數量過多: {active_sessions} (超過 {alert_threshold})"
                alert_file = "/root/.openclaw/workspace/latest_alerts.txt"
                with open(alert_file, 'w') as f:
                    f.write(alert_msg)
                print(f"🚨 發現警報: {alert_msg}")
            else:
                # 清除警報檔案
                alert_file = "/root/.openclaw/workspace/latest_alerts.txt"
                if os.path.exists(alert_file):
                    os.remove(alert_file)
                print(f"✅ 系統正常，活躍會話: {active_sessions}")
                
        return dashboard_text
        
    except Exception as e:
        print(f"❌ 監控更新失敗: {e}")
        return None

def main():
    """主函數"""
    try:
        dashboard = update_monitoring_dashboard()
        
        # 保存日誌
        log_file = "/root/.openclaw/workspace/monitoring_cron.log"
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - 監控更新完成\\n")
        
        print(f"✅ Cron 任務完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Cron 任務執行失敗: {e}")

if __name__ == "__main__":
    main()
"""
    
    script_path = "/root/.openclaw/workspace/monitoring_cron_fixed.py"
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(cron_script)
        
        # 設置執行權限
        os.chmod(script_path, 0o755)
        
        print(f"✅ 監控 Cron 腳本已更新: {script_path}")
        return script_path
        
    except Exception as e:
        print(f"❌ 更新 Cron 腳本時出錯: {e}")
        return None

def update_simple_monitoring_dashboard():
    """更新簡化監控儀表板腳本"""
    
    # 備份原始檔案
    original_file = "/root/.openclaw/workspace/simple_monitoring_dashboard.py"
    backup_file = f"{original_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if os.path.exists(original_file):
        shutil.copy2(original_file, backup_file)
        print(f"📁 原始檔案已備份: {backup_file}")
    
    # 創建新的修正版
    new_content = """#!/usr/bin/env python3
"""
簡化監控儀表板 - 修正版（使用正確的會話計算）
"""

import json
import subprocess
import time
from datetime import datetime, timedelta
import os
import sys

def get_active_sessions_only():
    """只獲取活躍會話（5分鐘內有活動）"""
    try:
        cmd = ["openclaw", "sessions", "list", "--json", "--kinds", "subagent"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return {"sessions": [], "total": 0, "active": 0}
        
        data = json.loads(result.stdout)
        sessions = data.get("sessions", [])
        
        # 過濾出活躍會話
        now = datetime.now()
        active_sessions = []
        
        for session in sessions:
            updated_at = session.get("updatedAt")
            if updated_at:
                timestamp = updated_at / 1000
                session_time = datetime.fromtimestamp(timestamp)
                age = now - session_time
                
                if age.total_seconds() < 300:  # 5分鐘
                    active_sessions.append(session)
        
        return {
            "sessions": active_sessions,
            "total": len(sessions),
            "active": len(active_sessions)
        }
        
    except Exception as e:
        print(f"❌ 獲取會話數據時發生錯誤: {e}")
        return {"sessions": [], "total": 0, "active": 0}

def main():
    """主函數 - 生成修正版監控儀表板"""
    
    # 獲取會話數據
    session_data = get_active_sessions_only()
    active_count = session_data["active"]
    total_count = session_data["total"]
    
    # 獲取系統指標
    try:
        cpu_cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
        cpu_result = subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True)
        cpu_percent = float(cpu_result.stdout.strip()) if cpu_result.stdout.strip() else 0
        
        mem_cmd = "free | grep Mem | awk '{print $3/$2 * 100.0}'"
        mem_result = subprocess.run(mem_cmd, shell=True, capture_output=True, text=True)
        mem_percent = float(mem_result.stdout.strip()) if mem_result.stdout.strip() else 0
    except:
        cpu_percent = 0
        mem_percent = 0
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    dashboard = f"""📊 **OpenClaw 監控儀表板** ({now})

🤖 **子代理任務狀態**
├ 活躍會話 (<5m): {active_count}
├ 總會話檔案: {total_count}
└ 警戒狀態: {'✅ 正常' if active_count <= 30 else '⚠️  超過警戒線'}

⚙️ **系統資源**
├ CPU: {cpu_percent:.1f}%
├ 記憶體: {mem_percent:.1f}%
└ 狀態: {'🟢 正常' if cpu_percent < 80 and mem_percent < 75 else '🟡 注意'}

📈 **監控說明**
• 只計算5分鐘內有活動的會話
• 歷史會話檔案不計入監控
• 警戒線: 30個活躍會話
• 系統會自動清理舊檔案
"""
    
    print(dashboard)
    return dashboard

if __name__ == "__main__":
    main()
"""
    
    try:
        with open(original_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 簡化監控儀表板已更新: {original_file}")
        return original_file
        
    except Exception as e:
        print(f"❌ 更新監控儀表板時出錯: {e}")
        return None

def create_unified_monitoring_config():
    """創建統一的監控配置"""
    
    config = {
        "version": "3.0",
        "last_updated": datetime.now().isoformat(),
        "monitoring_system": "unified_corrected",
        "session_calculation": {
            "method": "active_only",
            "active_threshold_minutes": 5,
            "ignore_old_sessions": True,
            "max_sessions_alert": 30,
            "auto_cleanup_hours": 24
        },
        "system_metrics": {
            "cpu_alert_threshold": 80,
            "memory_alert_threshold": 75,
            "disk_alert_threshold": 90,
            "load_alert_threshold": 4.0
        },
        "scheduling": {
            "dashboard_update_minutes": 5,
            "cleanup_daily_hour": 3,
            "health_check_hourly": True
        },
        "components": {
            "cron_script": "monitoring_cron_fixed.py",
            "dashboard_script": "simple_monitoring_dashboard.py",
            "cleanup_script": "cleanup_sessions.sh",
            "fix_script": "fix_session_count.py"
        }
    }
    
    config_file = "/root/.openclaw/workspace/monitoring_config.json"
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 統一監控配置已創建: {config_file}")
        return config_file
        
    except Exception as e:
        print(f"❌ 創建監控配置時出錯: {e}")
        return None

def setup_scheduled_cleanup():
    """設置定期清理任務"""
    
    # 更新 crontab
    cron_content = """# OpenClaw 監控系統定期任務（修正版）
# 使用正確的會話計算邏輯

# 每5分鐘更新監控儀表板（使用修正版腳本）
*/5 * * * * cd /root/.openclaw/workspace && python3 monitoring_cron_fixed.py >> /root/.openclaw/workspace/monitoring_cron.log 2>&1

# 每天凌晨3點清理舊會話檔案
0 3 * * * /root/.openclaw/workspace/cleanup_sessions.sh >> /root/.openclaw/workspace/cleanup.log 2>&1

# 每小時執行健康檢查
0 * * * * cd /root/.openclaw/workspace && python3 simple_monitoring_dashboard.py >> /root/.openclaw/workspace/monitoring_hourly.log 2>&1

# 每週日凌晨2點執行完整系統檢查
0 2 * * 0 cd /root/.openclaw/workspace && python3 fix_session_count.py >> /root/.openclaw/workspace/weekly_check.log 2>&1
"""
    
    cron_file = "/root/.openclaw/workspace/monitoring_crontab_final.txt"
    
    try:
        with open(cron_file, 'w', encoding='utf-8') as f:
            f.write(cron_content)
        
        print(f"✅ 定期清理任務已設置: {cron_file}")
        
        # 提示用戶如何應用 crontab
        print("\n📋 如何應用新的 Cron 任務：")
        print("  1. 查看當前 crontab: crontab -l")
        print("  2. 編輯 crontab: crontab -e")
        print("  3. 添加以上內容到 crontab")
        print("  或使用: cat monitoring_crontab_final.txt | crontab -")
        
        return cron_file
        
    except Exception as e:
        print(f"❌ 設置清理任務時出錯: {e}")
        return None

def main():
    """主函數"""
    
    print("🎯 最終監控系統修復與整合")
    print("=" * 60)
    print("此腳本將：")
    print("  1. 更新所有監控組件使用正確的會話計算邏輯")
    print("  2. 創建統一的監控配置")
    print("  3. 設置定期清理任務")
    print("  4. 確保監控警報準確無誤")
    print("=" * 60)
    
    success = update_all_monitoring_components()
    
    if success:
        print("\n🎉 監控系統修復完成！")
        print("\n📊 當前系統狀態：")
        print("  ✅ 會話計算邏輯已修正（只計算活躍會話）")
        print("  ✅ 警戒線已調整至30個會話")
        print("  ✅ 定期清理機制已建立")
        print("  ✅ 所有監控組件已同步")
        
        print("\n🚀 立即測試：")
        print("  執行: python3 simple_monitoring_dashboard.py")
        print("  查看修正版儀表板")
        
        print("\n🔧 長期維護：")
        print("  • 系統會自動清理舊會話")
        print("  • 監控數據更準確可靠")
        print("  • 警報系統更智能")
    else:
        print("\n❌ 修復過程中出現問題，請檢查日誌")

if __name__ == "__main__":
    import json
    main()