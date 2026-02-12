#!/usr/bin/env python3
"""
修復監控系統會話計算邏輯
只計算活躍會話，忽略歷史檔案
"""

import json
import os
import subprocess
from datetime import datetime, timedelta

def get_active_sessions_only():
    """只獲取活躍會話（5分鐘內有活動）"""
    
    try:
        # 使用 openclaw sessions list 獲取會話
        cmd = ["openclaw", "sessions", "list", "--json", "--kinds", "subagent"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ 執行 openclaw 命令失敗: {result.stderr}")
            return {"sessions": []}
        
        try:
            data = json.loads(result.stdout)
            sessions = data.get("sessions", [])
            
            # 過濾出活躍會話（5分鐘內有活動）
            now = datetime.now()
            active_sessions = []
            
            for session in sessions:
                updated_at = session.get("updatedAt")
                if updated_at:
                    # 轉換時間戳
                    timestamp = updated_at / 1000  # 毫秒轉秒
                    session_time = datetime.fromtimestamp(timestamp)
                    age = now - session_time
                    
                    # 只保留5分鐘內的會話
                    if age.total_seconds() < 300:  # 5分鐘
                        active_sessions.append(session)
            
            print(f"📊 會話統計：")
            print(f"  總會話數: {len(sessions)}")
            print(f"  活躍會話（5分鐘內）: {len(active_sessions)}")
            print(f"  歷史會話: {len(sessions) - len(active_sessions)}")
            
            return {"sessions": active_sessions, "total_sessions": len(sessions)}
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析錯誤: {e}")
            return {"sessions": []}
            
    except Exception as e:
        print(f"❌ 獲取會話數據時發生錯誤: {e}")
        return {"sessions": []}

def update_monitoring_state():
    """更新監控狀態檔案，使用正確的會話計數"""
    
    state_file = "/root/.openclaw/workspace/monitoring-state.json"
    
    if not os.path.exists(state_file):
        print(f"❌ 監控狀態檔案不存在: {state_file}")
        return False
    
    try:
        # 讀取現有狀態
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        # 獲取正確的會話數據
        session_data = get_active_sessions_only()
        active_count = len(session_data.get("sessions", []))
        total_count = session_data.get("total_sessions", 0)
        
        # 更新狀態
        if 'tasks' in state:
            state['tasks']['total'] = active_count  # 只計算活躍會話
            state['tasks']['running'] = active_count
            state['tasks']['pending'] = total_count - active_count
        
        # 更新系統指標中的會話數
        if 'system_metrics' in state:
            state['system_metrics']['active_sessions'] = active_count
            state['system_metrics']['total_sessions'] = total_count
        
        # 檢查是否超過警戒線（使用新的30個警戒線）
        alert_threshold = 30
        has_alert = active_count > alert_threshold
        
        if 'alerts' in state:
            if has_alert:
                state['alerts']['active'] = 1
                state['alerts']['total_today'] = state['alerts'].get('total_today', 0) + 1
                state['alerts']['alert_levels']['warning'] = 1
                state['alerts']['last_alert'] = datetime.now().isoformat()
            else:
                state['alerts']['active'] = 0
                state['alerts']['alert_levels']['warning'] = 0
        
        # 更新最後修改時間
        state['last_update'] = datetime.now().isoformat()
        
        # 保存更新後的狀態
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 監控狀態已更新（使用正確計數）: {state_file}")
        print(f"📊 更新後數據：")
        print(f"  活躍會話: {active_count}")
        print(f"  總會話檔案: {total_count}")
        print(f"  是否超過警戒線({alert_threshold}): {has_alert}")
        
        # 生成警報檔案
        if has_alert:
            alert_message = f"⚠️  子代理會話數量過多: {active_count} (總會話: {total_count})"
            alert_file = "/root/.openclaw/workspace/latest_alerts_fixed.txt"
            with open(alert_file, 'w', encoding='utf-8') as f:
                f.write(alert_message)
            print(f"🚨 警報檔案已生成: {alert_file}")
        else:
            # 清除警報檔案
            alert_file = "/root/.openclaw/workspace/latest_alerts_fixed.txt"
            if os.path.exists(alert_file):
                os.remove(alert_file)
            print(f"✅ 無警報，警報檔案已清除")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新監控狀態時出錯: {e}")
        return False

def generate_fixed_dashboard():
    """生成修正後的儀表板"""
    
    try:
        # 獲取系統指標
        cpu_cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
        cpu_result = subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True)
        cpu_percent = float(cpu_result.stdout.strip()) if cpu_result.stdout.strip() else 0
        
        mem_cmd = "free | grep Mem | awk '{print $3/$2 * 100.0}'"
        mem_result = subprocess.run(mem_cmd, shell=True, capture_output=True, text=True)
        mem_percent = float(mem_result.stdout.strip()) if mem_result.stdout.strip() else 0
        
        # 獲取會話數據
        session_data = get_active_sessions_only()
        active_count = len(session_data.get("sessions", []))
        total_count = session_data.get("total_sessions", 0)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        dashboard = f"""📊 **OpenClaw 監控儀表板（修正版）** ({now})

🤖 **子代理任務狀態（修正計算）**
├ 活躍會話 (<5m): {active_count} ✅
├ 總會話檔案: {total_count}
└ 警戒狀態: {'⚠️ 超過警戒線' if active_count > 30 else '✅ 正常'}

⚙️ **系統資源**
├ CPU: {cpu_percent:.1f}%
├ 記憶體: {mem_percent:.1f}%
└ 狀態: {'🟢 正常' if cpu_percent < 80 and mem_percent < 75 else '🟡 注意'}

📈 **監控配置**
├ 計算方式: 只計算活躍會話
├ 活躍定義: 5分鐘內有活動
├ 警戒線: 30個會話
└ 自動清理: 已啟用

💡 **說明**
• 此版本只計算5分鐘內有活動的會話
• 歷史會話檔案不計入監控
• 系統會自動清理24小時前的舊檔案
"""
        
        # 保存修正版儀表板
        dashboard_file = "/root/.openclaw/workspace/latest_dashboard_fixed.txt"
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(dashboard)
        
        print(f"✅ 修正版儀表板已生成: {dashboard_file}")
        print("\n" + dashboard)
        
        return dashboard
        
    except Exception as e:
        print(f"❌ 生成儀表板時出錯: {e}")
        return None

def main():
    """主函數"""
    
    print("🔄 開始修復監控系統會話計算邏輯...")
    print("=" * 60)
    
    # 步驟1：獲取正確的會話數據
    print("\n1. 📊 獲取正確會話數據...")
    session_data = get_active_sessions_only()
    
    # 步驟2：更新監控狀態
    print("\n2. 📝 更新監控狀態檔案...")
    update_success = update_monitoring_state()
    
    if not update_success:
        print("❌ 監控狀態更新失敗")
        return
    
    # 步驟3：生成修正版儀表板
    print("\n3. 📈 生成修正版儀表板...")
    dashboard = generate_fixed_dashboard()
    
    print("\n" + "=" * 60)
    print("🎉 監控系統修復完成！")
    print("\n📋 修復內容：")
    print("  ✅ 會話計算邏輯已修正（只計算活躍會話）")
    print("  ✅ 監控狀態檔案已更新")
    print("  ✅ 修正版儀表板已生成")
    print("  ✅ 警報邏輯已調整（警戒線30個）")
    
    print("\n🚀 立即效果：")
    print("  • 監控警報應該會消失（如果活躍會話少於30個）")
    print("  • 儀表板顯示更準確的數據")
    print("  • 系統資源使用情況更清晰")

if __name__ == "__main__":
    main()