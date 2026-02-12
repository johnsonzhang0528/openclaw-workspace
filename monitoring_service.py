#!/usr/bin/env python3
"""
監控服務 - 定期更新監控儀表板並發送到 Telegram
"""

import time
import json
import subprocess
import threading
from datetime import datetime, timedelta
import os
import sys

class MonitoringService:
    """監控服務類別"""
    
    def __init__(self, update_interval=300):  # 5分鐘更新一次
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        self.last_update = None
        self.update_count = 0
        
        # 載入配置
        self.config = self.load_config()
        
    def load_config(self):
        """載入配置"""
        config_file = "/root/.openclaw/workspace/monitoring_config.json"
        default_config = {
            "telegram_enabled": False,
            "telegram_chat_id": "",
            "update_interval_seconds": 300,
            "dashboard_enabled": True,
            "alert_thresholds": {
                "cpu_percent": 80,
                "memory_percent": 75,
                "disk_percent": 90,
                "session_count": 20
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # 合併配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            print(f"⚠️  載入配置時出錯: {e}")
        
        return default_config
    
    def save_config(self):
        """保存配置"""
        config_file = "/root/.openclaw/workspace/monitoring_config.json"
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存: {config_file}")
        except Exception as e:
            print(f"❌ 保存配置時出錯: {e}")
    
    def run_monitoring_dashboard(self):
        """執行監控儀表板腳本"""
        try:
            script_path = "/root/.openclaw/workspace/simple_monitoring_dashboard.py"
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # 從輸出中提取儀表板內容
                lines = result.stdout.split('\n')
                dashboard_start = None
                dashboard_end = None
                
                for i, line in enumerate(lines):
                    if "📊 **OpenClaw 監控儀表板**" in line:
                        dashboard_start = i
                    elif "----------------------------------------" in line and dashboard_start is not None:
                        dashboard_end = i
                        break
                
                if dashboard_start is not None and dashboard_end is not None:
                    dashboard_lines = lines[dashboard_start:dashboard_end]
                    dashboard_text = '\n'.join(dashboard_lines)
                    
                    # 保存儀表板
                    dashboard_file = "/root/.openclaw/workspace/latest_dashboard.txt"
                    with open(dashboard_file, 'w') as f:
                        f.write(dashboard_text)
                    
                    print(f"✅ 監控儀表板已更新 ({len(dashboard_text)} 字元)")
                    return dashboard_text
                else:
                    print("⚠️  無法從輸出中提取儀表板內容")
                    return None
            else:
                print(f"❌ 執行監控腳本失敗: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("❌ 監控腳本執行超時")
            return None
        except Exception as e:
            print(f"❌ 執行監控時出錯: {e}")
            return None
    
    def send_to_telegram(self, message):
        """發送到 Telegram"""
        if not self.config.get("telegram_enabled", False):
            return False
        
        chat_id = self.config.get("telegram_chat_id", "")
        if not chat_id:
            print("⚠️  Telegram Chat ID 未設定")
            return False
        
        try:
            # 使用 OpenClaw message 工具發送
            cmd = [
                "openclaw", "message", "send",
                "--channel", "telegram",
                "--target", chat_id,
                "--message", message
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ 監控儀表板已發送到 Telegram")
                return True
            else:
                print(f"❌ 發送到 Telegram 失敗: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 發送到 Telegram 時出錯: {e}")
            return False
    
    def check_alerts(self, dashboard_text):
        """檢查警報條件"""
        alerts = []
        
        try:
            # 讀取最新的監控狀態
            state_file = "/root/.openclaw/workspace/monitoring-state.json"
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                # 檢查系統指標
                metrics = state.get("system_metrics", {})
                thresholds = self.config.get("alert_thresholds", {})
                
                # CPU 警報
                cpu_load = metrics.get("cpu_load", 0)
                cpu_threshold = thresholds.get("cpu_percent", 80)
                if cpu_load > cpu_threshold:
                    alerts.append(f"⚠️  CPU 使用率過高: {cpu_load:.1f}% (閾值: {cpu_threshold}%)")
                
                # 記憶體警報
                memory_percent = metrics.get("memory_percent", 0)
                memory_threshold = thresholds.get("memory_percent", 75)
                if memory_percent > memory_threshold:
                    alerts.append(f"⚠️  記憶體使用率過高: {memory_percent:.1f}% (閾值: {memory_threshold}%)")
                
                # 磁碟警報
                disk_percent = metrics.get("disk_percent", 0)
                disk_threshold = thresholds.get("disk_percent", 90)
                if disk_percent > disk_threshold:
                    alerts.append(f"⚠️  磁碟使用率過高: {disk_percent:.1f}% (閾值: {disk_threshold}%)")
                
                # 會話數量警報
                tasks = state.get("tasks", {})
                session_count = tasks.get("total", 0)
                session_threshold = thresholds.get("session_count", 20)
                if session_count > session_threshold:
                    alerts.append(f"⚠️  子代理會話數量過多: {session_count} (閾值: {session_threshold})")
        
        except Exception as e:
            print(f"❌ 檢查警報時出錯: {e}")
        
        return alerts
    
    def monitoring_loop(self):
        """監控循環"""
        print(f"🔄 監控服務啟動，更新間隔: {self.update_interval} 秒")
        
        while self.running:
            try:
                print(f"\n⏰ 第 {self.update_count + 1} 次監控更新...")
                self.last_update = datetime.now()
                
                # 執行監控儀表板
                dashboard_text = self.run_monitoring_dashboard()
                
                if dashboard_text:
                    # 檢查警報
                    alerts = self.check_alerts(dashboard_text)
                    
                    # 如果有警報，添加到儀表板
                    if alerts:
                        alert_text = "\n🚨 **系統警報**\n" + "\n".join(alerts)
                        dashboard_text += alert_text
                        
                        # 發送警報到 Telegram
                        if self.config.get("telegram_enabled", False):
                            self.send_to_telegram(alert_text)
                    
                    # 發送完整儀表板到 Telegram（可選）
                    if self.config.get("telegram_enabled", False) and self.update_count % 12 == 0:  # 每小時發送一次
                        self.send_to_telegram(dashboard_text)
                
                self.update_count += 1
                
                # 等待下一次更新
                for _ in range(self.update_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n🛑 收到停止信號")
                self.running = False
                break
            except Exception as e:
                print(f"❌ 監控循環中出錯: {e}")
                time.sleep(60)  # 出錯後等待1分鐘再試
    
    def start(self):
        """啟動監控服務"""
        if self.running:
            print("⚠️  監控服務已在運行中")
            return
        
        print("🚀 啟動監控服務...")
        self.running = True
        self.thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.thread.start()
        print("✅ 監控服務已啟動")
    
    def stop(self):
        """停止監控服務"""
        print("🛑 停止監控服務...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        print("✅ 監控服務已停止")
    
    def status(self):
        """顯示服務狀態"""
        status_info = {
            "running": self.running,
            "update_count": self.update_count,
            "last_update": self.last_update.isoformat() if self.last_update else "從未更新",
            "update_interval": self.update_interval,
            "telegram_enabled": self.config.get("telegram_enabled", False)
        }
        
        print("📊 監控服務狀態:")
        for key, value in status_info.items():
            print(f"  {key}: {value}")
        
        return status_info

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw 監控服務")
    parser.add_argument("action", choices=["start", "stop", "status", "update", "test"],
                       help="執行動作")
    parser.add_argument("--interval", type=int, default=300,
                       help="更新間隔（秒），預設 300 秒（5分鐘）")
    parser.add_argument("--telegram", action="store_true",
                       help="啟用 Telegram 通知")
    parser.add_argument("--chat-id", type=str,
                       help="Telegram Chat ID")
    
    args = parser.parse_args()
    
    # 創建服務實例
    service = MonitoringService(update_interval=args.interval)
    
    if args.telegram:
        service.config["telegram_enabled"] = True
        if args.chat_id:
            service.config["telegram_chat_id"] = args.chat_id
        service.save_config()
    
    if args.action == "start":
        service.start()
        
        # 保持主線程運行
        try:
            while service.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 收到停止信號")
            service.stop()
            
    elif args.action == "stop":
        service.stop()
        
    elif args.action == "status":
        service.status()
        
    elif args.action == "update":
        print("🔄 手動執行監控更新...")
        dashboard = service.run_monitoring_dashboard()
        if dashboard:
            print("✅ 監控更新完成")
            
            # 檢查警報
            alerts = service.check_alerts(dashboard)
            if alerts:
                print("\n🚨 發現警報:")
                for alert in alerts:
                    print(f"  {alert}")
        
    elif args.action == "test":
        print("🧪 測試監控系統...")
        
        # 測試監控儀表板
        print("1. 測試監控儀表板生成...")
        dashboard = service.run_monitoring_dashboard()
        if dashboard:
            print(f"✅ 儀表板生成成功 ({len(dashboard)} 字元)")
            print("\n儀表板預覽:")
            print("-"*40)
            print(dashboard[:500] + "..." if len(dashboard) > 500 else dashboard)
            print("-"*40)
        else:
            print("❌ 儀表板生成失敗")
        
        # 測試警報檢查
        print("\n2. 測試警報檢查...")
        alerts = service.check_alerts(dashboard if dashboard else "")
        if alerts:
            print(f"✅ 發現 {len(alerts)} 個警報:")
            for alert in alerts:
                print(f"  {alert}")
        else:
            print("✅ 無警報，系統正常")
        
        # 測試 Telegram 發送
        if service.config.get("telegram_enabled", False):
            print("\n3. 測試 Telegram 發送...")
            test_message = "🧪 監控服務測試訊息 - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            success = service.send_to_telegram(test_message)
            if success:
                print("✅ Telegram 發送測試成功")
            else:
                print("❌ Telegram 發送測試失敗")
        else:
            print("\n3. Telegram 通知未啟用（使用 --telegram 啟用）")

if __name__ == "__main__":
    main()