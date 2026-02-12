#!/usr/bin/env python3
"""
效能監控儀表板整合測試
"""

import asyncio
import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch, AsyncMock
import sys

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance_monitor.main import PerformanceMonitor
from performance_monitor.resource_monitor import ResourceMonitor, ResourceMetrics
from performance_monitor.dashboard import PerformanceDashboard
from performance_monitor.config import Config

class TestPerformanceMonitor(unittest.TestCase):
    """效能監控測試類別"""
    
    def setUp(self):
        """測試設置"""
        # 創建臨時配置檔案
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        
        config_data = {
            "collection_interval": 0.1,  # 快速收集用於測試
            "metrics_history_size": 10,
            "process_history_size": 5,
            "top_processes_limit": 3,
            "cpu_alert_threshold": 90,
            "memory_alert_threshold": 85,
            "disk_alert_threshold": 80,
            "max_alerts": 100,
            "dashboard_update_interval": 0.1,
            "log_level": "INFO"
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
            
    def tearDown(self):
        """測試清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_config_loading(self):
        """測試配置載入"""
        config = Config(self.config_file)
        
        self.assertEqual(config.collection_interval, 0.1)
        self.assertEqual(config.metrics_history_size, 10)
        self.assertEqual(config.cpu_alert_threshold, 90)
        self.assertEqual(config.log_level, "INFO")
        
    @patch('performance_monitor.resource_monitor.psutil')
    def test_resource_monitor_metrics(self, mock_psutil):
        """測試資源監控指標收集"""
        # 模擬 psutil 返回值
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.virtual_memory.return_value = Mock(percent=65.2, used=1024*1024*512, total=1024*1024*1024)
        mock_psutil.disk_usage.return_value = Mock(percent=45.3, used=1024*1024*1024*100, total=1024*1024*1024*256)
        mock_psutil.net_io_counters.return_value = Mock(bytes_sent=1024*1024*10, bytes_recv=1024*1024*50)
        mock_psutil.getloadavg.return_value = (1.2, 1.5, 1.8)
        mock_psutil.swap_memory.return_value = Mock(percent=30.0, used=1024*1024*256, total=1024*1024*1024)
        mock_psutil.pids.return_value = [1, 2, 3, 4, 5]
        
        config = Config(self.config_file)
        monitor = ResourceMonitor(config)
        
        # 測試指標收集
        metrics = asyncio.run(monitor._collect_metrics())
        
        self.assertIsInstance(metrics, ResourceMetrics)
        self.assertEqual(metrics.cpu_percent, 25.5)
        self.assertEqual(metrics.memory_percent, 65.2)
        self.assertEqual(metrics.disk_usage_percent, 45.3)
        self.assertEqual(metrics.load_average, (1.2, 1.5, 1.8))
        
    def test_dashboard_text_generation(self):
        """測試儀表板文字生成"""
        config = Config(self.config_file)
        dashboard = PerformanceDashboard(config)
        
        # 測試數據
        metrics = {
            "cpu": {
                "percent": 25.5,
                "load_average": (1.2, 1.5, 1.8)
            },
            "memory": {
                "percent": 65.2,
                "used": 1024*1024*512,
                "total": 1024*1024*1024,
                "used_formatted": "512.0 MB",
                "total_formatted": "1.0 GB"
            },
            "disk": {
                "percent": 45.3,
                "used": 1024*1024*1024*100,
                "total": 1024*1024*1024*256,
                "used_formatted": "100.0 GB",
                "total_formatted": "256.0 GB"
            },
            "network": {
                "sent_rate_formatted": "1.5 MB/s",
                "received_rate_formatted": "5.2 MB/s"
            },
            "system": {
                "process_count": 5,
                "swap_percent": 30.0
            }
        }
        
        trends = {
            "cpu": {
                "average": 22.5,
                "trend": "increasing"
            },
            "memory": {
                "average": 60.3,
                "trend": "decreasing"
            }
        }
        
        alerts = [
            {
                "type": "cpu",
                "level": "warning",
                "message": "CPU 使用率過高: 92.5%",
                "value": 92.5,
                "threshold": 90
            }
        ]
        
        top_processes = [
            {
                "name": "python3",
                "pid": 1234,
                "cpu_percent": 15.5,
                "memory_percent": 8.2
            }
        ]
        
        # 生成文字儀表板
        text_dashboard = dashboard.generate_text_dashboard(metrics, trends, alerts, top_processes)
        
        # 驗證輸出包含預期內容
        self.assertIn("效能監控儀表板", text_dashboard)
        self.assertIn("CPU 使用情況", text_dashboard)
        self.assertIn("記憶體使用情況", text_dashboard)
        self.assertIn("CPU 使用率過高", text_dashboard)
        self.assertIn("python3", text_dashboard)
        
    @patch('performance_monitor.resource_monitor.psutil')
    def test_alert_generation(self, mock_psutil):
        """測試警報生成"""
        # 模擬高資源使用率
        mock_psutil.cpu_percent.return_value = 95.5  # 超過閾值
        mock_psutil.virtual_memory.return_value = Mock(percent=90.2, used=1024*1024*900, total=1024*1024*1024)
        mock_psutil.disk_usage.return_value = Mock(percent=85.3, used=1024*1024*1024*200, total=1024*1024*1024*256)
        mock_psutil.net_io_counters.return_value = Mock(bytes_sent=0, bytes_recv=0)
        mock_psutil.getloadavg.return_value = (0, 0, 0)
        mock_psutil.swap_memory.return_value = Mock(percent=0, used=0, total=0)
        mock_psutil.pids.return_value = []
        
        config = Config(self.config_file)
        monitor = ResourceMonitor(config)
        
        # 收集指標
        metrics = asyncio.run(monitor._collect_metrics())
        
        # 檢查警報
        asyncio.run(monitor._check_alerts(metrics))
        alerts = asyncio.run(monitor.get_active_alerts())
        
        # 應該有 CPU 和記憶體警報
        self.assertGreaterEqual(len(alerts), 2)
        
        # 檢查警報類型
        alert_types = [alert['type'] for alert in alerts]
        self.assertIn('cpu', alert_types)
        self.assertIn('memory', alert_types)
        
    def test_ascii_chart_generation(self):
        """測試 ASCII 圖表生成"""
        from performance_monitor.utils import create_ascii_chart
        
        # 測試不同值
        chart_50 = create_ascii_chart(50, 0, 100, width=20)
        chart_75 = create_ascii_chart(75, 0, 100, width=20)
        chart_25 = create_ascii_chart(25, 0, 100, width=20)
        
        # 驗證圖表長度
        self.assertEqual(len(chart_50), 20)
        self.assertEqual(len(chart_75), 20)
        self.assertEqual(len(chart_25), 20)
        
        # 驗證圖表包含正確的字符
        self.assertIn('█', chart_50)
        self.assertIn('░', chart_50)
        
    @patch('performance_monitor.resource_monitor.psutil')
    async def test_monitor_integration(self, mock_psutil):
        """測試監控整合"""
        # 模擬 psutil
        mock_psutil.cpu_percent.return_value = 30.0
        mock_psutil.virtual_memory.return_value = Mock(percent=50.0, used=1024*1024*500, total=1024*1024*1024)
        mock_psutil.disk_usage.return_value = Mock(percent=40.0, used=1024*1024*1024*100, total=1024*1024*1024*256)
        mock_psutil.net_io_counters.side_effect = [
            Mock(bytes_sent=0, bytes_recv=0),
            Mock(bytes_sent=1024*1024, bytes_recv=1024*1024*2)
        ]
        mock_psutil.getloadavg.return_value = (1.0, 1.5, 2.0)
        mock_psutil.swap_memory.return_value = Mock(percent=20.0, used=1024*1024*200, total=1024*1024*1024)
        mock_psutil.pids.return_value = [1, 2, 3]
        
        config = Config(self.config_file)
        monitor = ResourceMonitor(config)
        
        # 啟動監控
        await monitor.start()
        
        # 等待一次收集
        await asyncio.sleep(0.15)
        
        # 獲取指標
        metrics = await monitor.get_current_metrics()
        trends = await monitor.get_trends(hours=1)
        alerts = await monitor.get_active_alerts()
        
        # 驗證數據
        self.assertIsNotNone(metrics)
        self.assertIn('cpu', metrics)
        self.assertIn('memory', metrics)
        
        # 停止監控
        await monitor.stop()
        
    def test_metrics_formatting(self):
        """測試指標格式化"""
        from performance_monitor.utils import format_bytes, format_percentage
        
        # 測試位元組格式化
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024*1024), "1.0 MB")
        self.assertEqual(format_bytes(1024*1024*1024), "1.0 GB")
        
        # 測試百分比格式化
        self.assertEqual(format_percentage(50.123), "50.1%")
        self.assertEqual(format_percentage(75.678), "75.7%")
        self.assertEqual(format_percentage(100.0), "100.0%")

class TestPerformanceMonitorMain(unittest.TestCase):
    """效能監控主程序測試"""
    
    def setUp(self):
        """測試設置"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """測試清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    @patch('performance_monitor.main.PerformanceMonitor.start')
    @patch('performance_monitor.main.PerformanceMonitor.stop')
    async def test_main_lifecycle(self, mock_stop, mock_start):
        """測試主程序生命週期"""
        # 模擬啟動和停止
        mock_start.return_value = None
        mock_stop.return_value = None
        
        # 創建監控實例
        monitor = PerformanceMonitor()
        
        # 測試啟動
        await monitor.start()
        mock_start.assert_called_once()
        
        # 測試停止
        await monitor.stop()
        mock_stop.assert_called_once()
        
    def test_monitor_status(self):
        """測試監控狀態"""
        config = Config(self.config_file)
        monitor = PerformanceMonitor(config)
        
        status = monitor.get_status()
        
        self.assertIn('running', status)
        self.assertIn('resource_monitor', status)
        self.assertIn('dashboard', status)
        self.assertIn('config', status)
        self.assertFalse(status['running'])  # 尚未啟動

if __name__ == '__main__':
    # 運行測試
    unittest.main()