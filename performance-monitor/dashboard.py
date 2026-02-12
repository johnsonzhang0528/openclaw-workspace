#!/usr/bin/env python3
"""
效能儀表板模組
提供圖形化儀表板顯示系統資源使用情況
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time

from .config import Config
from .utils import format_bytes, format_percentage, format_timestamp, create_ascii_chart

logger = logging.getLogger(__name__)

class PerformanceDashboard:
    """效能儀表板"""
    
    def __init__(self, config: Config):
        """初始化儀表板"""
        self.config = config
        self.running = False
        self.clients = set()
        self.update_interval = config.dashboard_update_interval
        
    async def start(self):
        """啟動儀表板"""
        if self.running:
            logger.warning("儀表板已在運行中")
            return
            
        logger.info("啟動效能儀表板...")
        self.running = True
        
        # 啟動更新任務
        self.update_task = asyncio.create_task(self._update_loop())
        
    async def stop(self):
        """停止儀表板"""
        if not self.running:
            return
            
        logger.info("停止效能儀表板...")
        self.running = False
        
        if hasattr(self, 'update_task'):
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
                
        logger.info("效能儀表板已停止")
        
    async def _update_loop(self):
        """更新循環"""
        while self.running:
            try:
                # 這裡可以實現定期更新邏輯
                # 例如：發送更新到連接的客戶端
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"儀表板更新循環錯誤: {e}")
                await asyncio.sleep(1)
                
    def generate_text_dashboard(self, metrics: Dict[str, Any], trends: Dict[str, Any], 
                               alerts: List[Dict[str, Any]], top_processes: List[Dict[str, Any]]) -> str:
        """生成文字儀表板"""
        lines = []
        
        # 標題
        lines.append("=" * 60)
        lines.append("效能監控儀表板")
        lines.append(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        
        # CPU 資訊
        lines.append("\n📊 CPU 使用情況:")
        lines.append(f"  使用率: {metrics.get('cpu', {}).get('percent', 0):.1f}%")
        if metrics.get('cpu', {}).get('load_average'):
            load_avg = metrics['cpu']['load_average']
            lines.append(f"  系統負載: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}")
        
        # 記憶體資訊
        mem = metrics.get('memory', {})
        lines.append("\n💾 記憶體使用情況:")
        lines.append(f"  使用率: {mem.get('percent', 0):.1f}%")
        lines.append(f"  已使用: {mem.get('used_formatted', 'N/A')} / {mem.get('total_formatted', 'N/A')}")
        
        # 磁碟資訊
        disk = metrics.get('disk', {})
        lines.append("\n💿 磁碟使用情況:")
        lines.append(f"  使用率: {disk.get('percent', 0):.1f}%")
        lines.append(f"  已使用: {disk.get('used_formatted', 'N/A')} / {disk.get('total_formatted', 'N/A')}")
        
        # 網路資訊
        net = metrics.get('network', {})
        lines.append("\n🌐 網路使用情況:")
        lines.append(f"  上傳: {net.get('sent_rate_formatted', 'N/A')}")
        lines.append(f"  下載: {net.get('received_rate_formatted', 'N/A')}")
        lines.append(f"  總上傳: {net.get('sent_formatted', 'N/A')}")
        lines.append(f"  總下載: {net.get('received_formatted', 'N/A')}")
        
        # 系統資訊
        sys_info = metrics.get('system', {})
        lines.append("\n⚙️ 系統資訊:")
        lines.append(f"  進程數量: {sys_info.get('process_count', 0)}")
        lines.append(f"  交換空間: {sys_info.get('swap_percent', 0):.1f}%")
        lines.append(f"  交換使用: {sys_info.get('swap_used_formatted', 'N/A')} / {sys_info.get('swap_total_formatted', 'N/A')}")
        
        # 趨勢資訊
        if trends:
            lines.append("\n📈 趨勢分析 (最近1小時):")
            
            cpu_trend = trends.get('cpu', {})
            if cpu_trend:
                trend_arrow = "↗️" if cpu_trend.get('trend') == 'increasing' else "↘️"
                lines.append(f"  CPU: 平均 {cpu_trend.get('average', 0):.1f}% {trend_arrow}")
                
            mem_trend = trends.get('memory', {})
            if mem_trend:
                trend_arrow = "↗️" if mem_trend.get('trend') == 'increasing' else "↘️"
                lines.append(f"  記憶體: 平均 {mem_trend.get('average', 0):.1f}% {trend_arrow}")
                
            disk_trend = trends.get('disk', {})
            if disk_trend:
                trend_arrow = "↗️" if disk_trend.get('trend') == 'increasing' else "↘️"
                lines.append(f"  磁碟: 平均 {disk_trend.get('average', 0):.1f}% {trend_arrow}")
        
        # 警報資訊
        if alerts:
            lines.append("\n🚨 活動警報:")
            for alert in alerts[:5]:  # 顯示最多5個警報
                level_emoji = "⚠️" if alert.get('level') == 'warning' else "🔴"
                lines.append(f"  {level_emoji} {alert.get('message', 'Unknown alert')}")
            if len(alerts) > 5:
                lines.append(f"  ... 還有 {len(alerts) - 5} 個警報")
        
        # 頂部進程
        if top_processes:
            lines.append("\n🔝 頂部進程 (按CPU使用率):")
            for i, proc in enumerate(top_processes[:5], 1):
                lines.append(f"  {i}. {proc.get('name', 'Unknown')} (PID: {proc.get('pid')})")
                lines.append(f"     CPU: {proc.get('cpu_percent', 0):.1f}%, 記憶體: {proc.get('memory_percent', 0):.1f}%")
                cmdline = proc.get('cmdline', '')
                if cmdline and len(cmdline) > 50:
                    cmdline = cmdline[:47] + "..."
                if cmdline:
                    lines.append(f"     指令: {cmdline}")
        
        # ASCII 圖表
        lines.append("\n📊 CPU 使用率趨勢圖:")
        if metrics.get('cpu', {}).get('percent'):
            cpu_value = metrics['cpu']['percent']
            chart = create_ascii_chart(cpu_value, 0, 100, width=40)
            lines.append(f"  {chart}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
        
    def generate_html_dashboard(self, metrics: Dict[str, Any], trends: Dict[str, Any], 
                               alerts: List[Dict[str, Any]], top_processes: List[Dict[str, Any]]) -> str:
        """生成HTML儀表板"""
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>效能監控儀表板</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .dashboard {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .metric-card {{ background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .metric-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #2c3e50; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
                .alert-warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 5px 0; }}
                .alert-critical {{ background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin: 5px 0; }}
                .process-table {{ width: 100%; border-collapse: collapse; }}
                .process-table th, .process-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                .process-table th {{ background: #f2f2f2; }}
                .progress-bar {{ height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; }}
                .progress-fill {{ height: 100%; background: #3498db; }}
                .trend-up {{ color: #e74c3c; }}
                .trend-down {{ color: #2ecc71; }}
            </style>
        </head>
        <body>
            <div class="dashboard">
                <div class="header">
                    <h1>效能監控儀表板</h1>
                    <p>更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="metrics-grid">
                    <!-- CPU 卡片 -->
                    <div class="metric-card">
                        <div class="metric-title">📊 CPU 使用率</div>
                        <div class="metric-value">{metrics.get('cpu', {}).get('percent', 0):.1f}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {metrics.get('cpu', {}).get('percent', 0)}%"></div>
                        </div>
                    </div>
                    
                    <!-- 記憶體卡片 -->
                    <div class="metric-card">
                        <div class="metric-title">💾 記憶體使用率</div>
                        <div class="metric-value">{metrics.get('memory', {}).get('percent', 0):.1f}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {metrics.get('memory', {}).get('percent', 0)}%"></div>
                        </div>
                        <p>{metrics.get('memory', {}).get('used_formatted', 'N/A')} / {metrics.get('memory', {}).get('total_formatted', 'N/A')}</p>
                    </div>
                    
                    <!-- 磁碟卡片 -->
                    <div class="metric-card">
                        <div class="metric-title">💿 磁碟使用率</div>
                        <div class="metric-value">{metrics.get('disk', {}).get('percent', 0):.1f}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {metrics.get('disk', {}).get('percent', 0)}%"></div>
                        </div>
                        <p>{metrics.get('disk', {}).get('used_formatted', 'N/A')} / {metrics.get('disk', {}).get('total_formatted', 'N/A')}</p>
                    </div>
                    
                    <!-- 網路卡片 -->
                    <div class="metric-card">
                        <div class="metric-title">🌐 網路流量</div>
                        <p>上傳: {metrics.get('network', {}).get('sent_rate_formatted', 'N/A')}</p>
                        <p>下載: {metrics.get('network', {}).get('received_rate_formatted', 'N/A')}</p>
                    </div>
                </div>
                
                <!-- 警報區域 -->
                {self._generate_alerts_html(alerts)}
                
                <!-- 進程表格 -->
                {self._generate_processes_html(top_processes)}
                
                <!-- 趨勢分析 -->
                {self._generate_trends_html(trends)}
            </div>
            
            <script>
                // 自動刷新頁面
                setTimeout(function() {{
                    location.reload();
                }}, 30000); // 每30秒刷新
            </script>
        </body>
        </html>
        """
        
        return html
        
    def _generate_alerts_html(self, alerts: List[Dict[str, Any]]) -> str:
        """生成警報HTML"""
        if not alerts:
            return ""
            
        html = '<div class="metric-card"><div class="metric-title">🚨 活動警報</div>'
        
        for alert in alerts[:10]:  # 顯示最多10個警報
            alert_class = "alert-critical" if alert.get('level') == 'critical' else "alert-warning"
            html += f'<div class="{alert_class}">{alert.get("message", "Unknown alert")}</div>'
            
        if len(alerts) > 10:
            html += f'<p>... 還有 {len(alerts) - 10} 個警報</p>'
            
        html += '</div>'
        return html
        
    def _generate_processes_html(self, processes: List[Dict[str, Any]]) -> str:
        """生成進程表格HTML"""
        if not processes:
            return ""
            
        html = '''
        <div class="metric-card">
            <div class="metric-title">🔝 頂部進程</div>
            <table class="process-table">
                <thead>
                    <tr>
                        <th>PID</th>
                        <th>名稱</th>
                        <th>CPU%</th>
                        <th>記憶體%</th>
                        <th>記憶體使用</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for proc in processes[:10]:  # 顯示最多10個進程
            html += f'''
                    <tr>
                        <td>{proc.get('pid', 'N/A')}</td>
                        <td>{proc.get('name', 'Unknown')}</td>
                        <td>{proc.get('cpu_percent', 0):.1f}%</td>
                        <td>{proc.get('memory_percent', 0):.1f}%</td>
                        <td>{proc.get('memory_rss_formatted', 'N/A')}</td>
                    </tr>
            '''
            
        html += '''
                </tbody>
            </table>
        </div>
        '''
        
        return html
        
    def _generate_trends_html(self, trends: Dict[str, Any]) -> str:
        """生成趨勢分析HTML"""
        if not trends:
            return ""
            
        html = '<div class="metric-card"><div class="metric-title">📈 趨勢分析 (最近1小時)</div>'
        
        for metric_name, trend_data in trends.items():
            if trend_data:
                trend_arrow = "↗️" if trend_data.get('trend') == 'increasing' else "↘️"
                trend_class = "trend-up" if trend_data.get('trend') == 'increasing' else "trend-down"
                
                html += f'''
                <p>
                    <strong>{metric_name.upper()}:</strong>
                    <span class="{trend_class}">
                        平均 {trend_data.get('average', 0):.1f}% {trend_arrow}
                        (最高: {trend_data.get('max', 0):.1f}%, 最低: {trend_data.get('min', 0):.1f}%)
                    </span>
                </p>
                '''
                
        html += '</div>'
        return html
        
    async def get_dashboard_data(self, resource_monitor) -> Dict[str, Any]:
        """獲取儀表板數據"""
        metrics = await resource_monitor.get_current_metrics()
        trends = await resource_monitor.get_trends(hours=1)
        alerts = await resource_monitor.get_active_alerts()
        top_processes = await resource_monitor.get_top_processes(count=10)
        
        return {
            "metrics": metrics,
            "trends": trends,
            "alerts": alerts,
            "top_processes": top_processes,
            "timestamp": time.time(),
            "timestamp_formatted": datetime.now().isoformat()
        }
        
    def get_status(self) -> Dict[str, Any]:
        """獲取儀表板狀態"""
        return {
            "running": self.running,
            "clients_count": len(self.clients),
            "update_interval": self.update_interval,
            "config": self.config.get_summary()
        }