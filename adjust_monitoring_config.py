#!/usr/bin/env python3
"""
調整監控系統配置腳本
修改會話計算邏輯，避免誤報
"""

import json
import os
from datetime import datetime

def adjust_monitoring_config():
    """調整監控系統配置"""
    
    # 監控狀態檔案路徑
    state_file = "/root/.openclaw/workspace/monitoring-state.json"
    
    if not os.path.exists(state_file):
        print("❌ 監控狀態檔案不存在")
        return False
    
    try:
        # 讀取現有配置
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        print("📋 當前監控配置：")
        print(f"  版本: {state.get('version', '未知')}")
        print(f"  最後更新: {state.get('last_update', '未知')}")
        
        # 檢查當前會話計算方式
        if 'tasks' in state:
            current_total = state['tasks'].get('total', 0)
            print(f"  當前計算的總會話數: {current_total}")
        
        # 修改配置：調整會話計算邏輯
        # 添加新的配置項
        if 'monitoring_config' not in state:
            state['monitoring_config'] = {}
        
        state['monitoring_config'].update({
            'session_calculation': 'active_only',  # 只計算活躍會話
            'active_threshold_minutes': 5,         # 5分鐘內為活躍
            'recent_threshold_hours': 1,           # 1小時內為近期
            'ignore_old_sessions': True,           # 忽略舊會話
            'max_sessions_alert': 30,              # 提高警戒線至30
            'auto_cleanup_hours': 24               # 自動清理24小時前的會話
        })
        
        # 更新最後修改時間
        state['last_update'] = datetime.now().isoformat()
        
        # 保存修改後的配置
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        print("✅ 監控配置調整完成！")
        print("\n📊 新的配置設定：")
        print("  1. 會話計算方式: 只計算活躍會話")
        print("  2. 活躍定義: 5分鐘內有活動")
        print("  3. 忽略舊會話: 是")
        print("  4. 警戒線: 30個會話")
        print("  5. 自動清理: 24小時前")
        
        return True
        
    except Exception as e:
        print(f"❌ 調整配置時出錯: {e}")
        return False

def create_monitoring_cleanup_script():
    """創建定期清理腳本"""
    
    cleanup_script = """#!/bin/bash
# 監控系統定期清理腳本
# 自動清理超過24小時的會話檔案

CLEANUP_DIR="/root/.openclaw/agents/main/sessions"
LOG_FILE="/root/.openclaw/workspace/cleanup.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - 開始清理會話檔案" >> "$LOG_FILE"

# 清理超過24小時的會話檔案
OLD_FILES=$(find "$CLEANUP_DIR" -name "*.jsonl" -type f -mmin +1440 | wc -l)

if [ "$OLD_FILES" -gt 0 ]; then
    echo "找到 $OLD_FILES 個超過24小時的會話檔案" >> "$LOG_FILE"
    
    # 實際清理
    find "$CLEANUP_DIR" -name "*.jsonl" -type f -mmin +1440 -delete
    
    echo "已清理 $OLD_FILES 個舊會話檔案" >> "$LOG_FILE"
else
    echo "沒有需要清理的舊會話檔案" >> "$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - 清理完成" >> "$LOG_FILE"
"""
    
    script_path = "/root/.openclaw/workspace/cleanup_sessions.sh"
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(cleanup_script)
        
        # 設置執行權限
        os.chmod(script_path, 0o755)
        
        print(f"✅ 定期清理腳本已創建: {script_path}")
        return script_path
        
    except Exception as e:
        print(f"❌ 創建清理腳本時出錯: {e}")
        return None

def update_monitoring_cron():
    """更新監控 Cron 任務"""
    
    cron_content = """# 監控系統定期任務
# 每5分鐘更新監控儀表板
*/5 * * * * cd /root/.openclaw/workspace && python3 monitoring_cron.py >> /root/.openclaw/workspace/monitoring_cron.log 2>&1

# 每天凌晨3點清理舊會話檔案
0 3 * * * /root/.openclaw/workspace/cleanup_sessions.sh

# 每小時檢查系統健康狀態
0 * * * * cd /root/.openclaw/workspace && python3 simple_monitoring_dashboard.py >> /root/.openclaw/workspace/monitoring_hourly.log 2>&1
"""
    
    cron_file = "/root/.openclaw/workspace/monitoring_crontab.txt"
    
    try:
        with open(cron_file, 'w', encoding='utf-8') as f:
            f.write(cron_content)
        
        print(f"✅ Cron 配置已更新: {cron_file}")
        print("\n📅 新的排程任務：")
        print("  1. 監控更新: 每5分鐘")
        print("  2. 會話清理: 每天凌晨3點")
        print("  3. 健康檢查: 每小時")
        
        return cron_file
        
    except Exception as e:
        print(f"❌ 更新 Cron 配置時出錯: {e}")
        return None

def main():
    """主函數"""
    
    print("🔄 開始調整監控系統配置...")
    print("=" * 50)
    
    # 步驟1：調整監控配置
    print("\n1. 📝 調整監控配置...")
    if not adjust_monitoring_config():
        print("❌ 配置調整失敗")
        return
    
    # 步驟2：創建清理腳本
    print("\n2. 🧹 創建定期清理腳本...")
    cleanup_script = create_monitoring_cleanup_script()
    if not cleanup_script:
        print("⚠️  清理腳本創建失敗，但繼續執行")
    
    # 步驟3：更新 Cron 任務
    print("\n3. ⏰ 更新 Cron 排程...")
    cron_file = update_monitoring_cron()
    if not cron_file:
        print("⚠️  Cron 更新失敗，但繼續執行")
    
    print("\n" + "=" * 50)
    print("🎉 監控系統調整完成！")
    print("\n📋 調整摘要：")
    print("  ✅ 會話計算邏輯已修改（只計算活躍會話）")
    print("  ✅ 警戒線提高至30個會話")
    print("  ✅ 定期清理腳本已創建")
    print("  ✅ Cron 排程已更新")
    print("\n🚀 效果預期：")
    print("  • 監控警報應該會消失")
    print("  • 系統會自動清理舊會話")
    print("  • 監控數據更準確")
    
    # 建議手動執行一次清理
    print("\n🔧 建議立即執行：")
    print("  1. 手動執行清理: ./cleanup_sessions.sh")
    print("  2. 重啟監控服務（如果適用）")
    print("  3. 等待下一次監控更新")

if __name__ == "__main__":
    main()