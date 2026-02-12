#!/usr/bin/env python3
"""
效能監控儀表板 - 主入口點
提供系統資源監控、效能指標收集和儀表板顯示功能
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import signal
import sys

from .resource_monitor import ResourceMonitor
from .dashboard import PerformanceDashboard
from .config import Config
from .utils import setup_logging, format_bytes, format_percentage

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """效能監控主類別"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化效能監控系統"""
        self.config = Config(config_path)
        self.resource_monitor = ResourceMonitor(self.config)
        self.dashboard = PerformanceDashboard(self.config)
        self.running = False
        
    async def start(self):
        """啟動監控系統"""
        if self.running:
            logger.warning("效能監控系統已在運行中")
            return
            
        logger.info("啟動效能監控系統...")
        
        # 設置信號處理
        self.setup_signal_handlers()
        
        try:
            # 啟動資源監控
            await self.resource_monitor.start()
            
            # 啟動儀表板
            await self.dashboard.start()
            
            self.running = True
            logger.info("效能監控系統啟動完成")
            
            # 主循環
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"效能監控系統運行時發生錯誤: {e}")
            await self.stop()
            
    async def stop(self):
        """停止監控系統"""
        if not self.running:
            return
            
        logger.info("停止效能監控系統...")
        self.running = False
        
        # 停止資源監控
        await self.resource_monitor.stop()
        
        # 停止儀表板
        await self.dashboard.stop()
        
        logger.info("效能監控系統已停止")
        
    def setup_signal_handlers(self):
        """設置信號處理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信號 {signum}, 正在停止...")
            asyncio.create_task(self.stop())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def get_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        return {
            "running": self.running,
            "resource_monitor": self.resource_monitor.get_status(),
            "dashboard": self.dashboard.get_status(),
            "config": self.config.get_summary()
        }
        
    async def get_metrics(self) -> Dict[str, Any]:
        """獲取當前指標"""
        metrics = await self.resource_monitor.get_current_metrics()
        return {
            "timestamp": asyncio.get_event_loop().time(),
            "metrics": metrics,
            "alerts": await self.resource_monitor.get_active_alerts(),
            "trends": await self.resource_monitor.get_trends()
        }

async def main():
    """主函數"""
    # 設置日誌
    setup_logging()
    
    # 創建監控實例
    monitor = PerformanceMonitor()
    
    try:
        # 啟動監控
        await monitor.start()
        
    except KeyboardInterrupt:
        logger.info("收到中斷信號")
    except Exception as e:
        logger.error(f"主程序錯誤: {e}")
    finally:
        # 確保清理
        await monitor.stop()

if __name__ == "__main__":
    # 運行主程序
    asyncio.run(main())