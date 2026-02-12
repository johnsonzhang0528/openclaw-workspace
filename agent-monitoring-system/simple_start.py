#!/usr/bin/env python3
"""
簡化版 Agent 監控系統啟動腳本
非互動式設計，避免阻塞問題
"""

import sys
import os
import time
import signal
import logging
from datetime import datetime

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_signal_handlers():
    """設置信號處理器"""
    def signal_handler(signum, frame):
        logger.info(f"收到信號 {signum}，正在關閉監控系統...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def check_environment():
    """檢查環境配置"""
    logger.info("檢查環境配置...")
    
    # 檢查環境變數檔案
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        logger.error(f"找不到環境變數檔案: {env_file}")
        logger.error("請複製 .env.example 為 .env 並設定 Telegram Bot Token")
        return False
    
    # 檢查必要配置
    required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_vars = []
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            for var in required_vars:
                if f'{var}=' in content:
                    # 檢查是否為預設值
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith(f'{var}='):
                            value = line.split('=', 1)[1].strip()
                            if 'your_' in value or 'dummy_' in value:
                                missing_vars.append(f"{var} (需要設定真實值)")
                            break
                else:
                    missing_vars.append(var)
    except Exception as e:
        logger.error(f"讀取環境變數檔案失敗: {e}")
        return False
    
    if missing_vars:
        logger.error("缺少必要配置:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("請編輯 .env 檔案設定正確的 Telegram Bot Token 和 Chat ID")
        return False
    
    logger.info("環境配置檢查通過")
    return True

def test_telegram_integration():
    """測試 Telegram 整合"""
    logger.info("測試 Telegram 整合...")
    
    try:
        import config
        import telegram_dashboard
        
        # 載入配置
        cfg = config.config
        
        if not cfg.telegram.bot_token or not cfg.telegram.chat_id:
            logger.warning("Telegram Bot Token 或 Chat ID 未設定")
            logger.warning("請設定 .env 檔案中的 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID")
            return False
        
        # 創建模擬對象進行測試
        class MockSessionTracker:
            def get_active_sessions(self, limit=10):
                return []
            def get_session_count(self):
                return {'total': 0, 'active': 0, 'completed': 0, 'failed': 0}
            def get_statistics(self):
                return {'today_sessions': 0, 'completed_sessions': 0, 'failed_sessions': 0, 'avg_runtime_minutes': 0, 'success_rate': 0}
        
        class MockResourceMonitor:
            def get_current_metrics(self):
                class MockMetrics:
                    cpu_percent = 25.5
                    memory_percent = 45.8
                    disk_percent = 32.1
                    network_sent_mb = 45.4
                    network_recv_mb = 32.7
                    load_avg_1m = 0.5
                return MockMetrics()
        
        tracker = MockSessionTracker()
        monitor = MockResourceMonitor()
        dashboard = telegram_dashboard.TelegramDashboard(tracker, monitor)
        
        # 生成測試儀表板
        test_dashboard = dashboard.generate_full_dashboard()
        
        logger.info(f"Telegram 儀表板生成測試成功，長度: {len(test_dashboard)} 字元")
        
        return True
        
    except Exception as e:
        logger.error(f"Telegram 整合測試失敗: {e}")
        return False

def start_monitoring_system():
    """啟動監控系統"""
    logger.info("啟動 Agent 監控系統...")
    
    try:
        from agent_monitor import AgentMonitor
        
        # 創建監控器
        monitor = AgentMonitor()
        
        logger.info(f"監控系統初始化完成，開始時間: {monitor.start_time}")
        
        # 啟動監控
        logger.info("啟動監控服務...")
        monitor.start()
        
        logger.info("監控系統已啟動")
        
        # 保持運行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到停止信號，正在關閉監控系統...")
    except Exception as e:
        logger.error(f"監控系統啟動失敗: {e}")
        return False
    
    return True

def main():
    """主函數"""
    logger.info("=" * 60)
    logger.info("🤖 OpenClaw Agent 監控系統 (簡化版)")
    logger.info(f"啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # 設置信號處理
    setup_signal_handlers()
    
    # 檢查環境
    if not check_environment():
        logger.error("環境檢查失敗，無法啟動監控系統")
        return 1
    
    # 測試 Telegram 整合
    telegram_test_result = test_telegram_integration()
    if not telegram_test_result:
        logger.warning("Telegram 整合測試失敗，監控系統可能無法發送通知")
        logger.warning("繼續啟動監控系統...")
    
    # 啟動監控系統
    logger.info("=" * 60)
    success = start_monitoring_system()
    
    if success:
        logger.info("監控系統已正常關閉")
        return 0
    else:
        logger.error("監控系統啟動失敗")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)