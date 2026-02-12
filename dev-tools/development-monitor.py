#!/usr/bin/env python3
"""
開發進度監控工具
確保子代理以最快速度連續執行開發任務
"""

import os
import time
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional


class DevelopmentMonitor:
    """開發進度監控"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or os.path.join(
            os.path.expanduser('~'), '.openclaw', 'workspace'
        )
        self.progress_file = os.path.join(self.workspace_path, 'development-progress.json')
        self.stages = self._load_stages()
        
    def _load_stages(self) -> List[Dict]:
        """加載開發階段"""
        return [
            {
                'id': 'stage1',
                'name': '基礎架構準備',
                'description': '完善技能模板系統和開發工具',
                'expected_files': [
                    'skill-template/config.py',
                    'skill-template/telegram_ui.py',
                    'skill-template/utils.py',
                    'dev-tools/skill-builder.py',
                    'dev-tools/test-runner.py'
                ],
                'completed': False
            },
            {
                'id': 'stage2',
                'name': '技能市集瀏覽器',
                'description': '實現技能發現、安裝和管理功能',
                'expected_files': [
                    'skills-marketplace/',
                    'skills-marketplace/main.py',
                    'skills-marketplace/marketplace.py',
                    'skills-marketplace/install_manager.py'
                ],
                'completed': False
            },
            {
                'id': 'stage3',
                'name': '工作空間管理工具',
                'description': '實現檔案系統管理和專案工具',
                'expected_files': [
                    'workspace-manager/',
                    'workspace-manager/main.py',
                    'workspace-manager/file_explorer.py',
                    'workspace-manager/editor.py'
                ],
                'completed': False
            },
            {
                'id': 'stage4',
                'name': '效能監控儀表板',
                'description': '實現系統資源監控和警報功能',
                'expected_files': [
                    'performance-monitor/',
                    'performance-monitor/main.py',
                    'performance-monitor/resource_monitor.py',
                    'performance-monitor/dashboard.py'
                ],
                'completed': False
            },
            {
                'id': 'stage5',
                'name': '智慧快捷指令系統',
                'description': '實現自定義指令和模板系統',
                'expected_files': [
                    'smart-shortcuts/',
                    'smart-shortcuts/main.py',
                    'smart-shortcuts/shortcut_manager.py',
                    'smart-shortcuts/template_engine.py'
                ],
                'completed': False
            },
            {
                'id': 'stage6',
                'name': '整合與測試',
                'description': '整合所有功能並進行全面測試',
                'expected_files': [
                    'integration-tests/',
                    'test-results.json',
                    'user-docs.md'
                ],
                'completed': False
            },
            {
                'id': 'stage7',
                'name': '部署與優化',
                'description': '打包部署並進行效能優化',
                'expected_files': [
                    'deployment-packages/',
                    'performance-report.md',
                    'installation-guide.md'
                ],
                'completed': False
            }
        ]
    
    def check_progress(self) -> Dict:
        """檢查開發進度"""
        progress = {
            'timestamp': datetime.now().isoformat(),
            'total_stages': len(self.stages),
            'completed_stages': 0,
            'current_stage': None,
            'stage_details': []
        }
        
        for stage in self.stages:
            stage_info = {
                'id': stage['id'],
                'name': stage['name'],
                'completed': self._check_stage_completion(stage),
                'files_checked': [],
                'files_missing': []
            }
            
            # 檢查檔案
            for file_pattern in stage['expected_files']:
                file_path = os.path.join(self.workspace_path, file_pattern)
                if os.path.exists(file_path):
                    stage_info['files_checked'].append(file_pattern)
                else:
                    stage_info['files_missing'].append(file_pattern)
            
            # 更新完成狀態
            if stage_info['completed']:
                progress['completed_stages'] += 1
            elif progress['current_stage'] is None and not stage_info['completed']:
                progress['current_stage'] = stage['id']
            
            progress['stage_details'].append(stage_info)
        
        # 儲存進度
        self._save_progress(progress)
        
        return progress
    
    def _check_stage_completion(self, stage: Dict) -> bool:
        """檢查階段是否完成"""
        # 基礎架構階段需要至少80%的檔案存在
        if stage['id'] == 'stage1':
            required_files = 4  # 至少需要4個核心檔案
            existing_files = 0
            
            for file_pattern in stage['expected_files']:
                file_path = os.path.join(self.workspace_path, file_pattern)
                if os.path.exists(file_path):
                    existing_files += 1
            
            return existing_files >= required_files
        
        # 其他階段需要目錄存在且包含主檔案
        else:
            # 檢查主目錄
            main_dir = stage['expected_files'][0].rstrip('/')
            dir_path = os.path.join(self.workspace_path, main_dir)
            
            if not os.path.exists(dir_path):
                return False
            
            # 檢查主要檔案
            required_files = ['main.py']
            for req_file in required_files:
                file_path = os.path.join(dir_path, req_file)
                if not os.path.exists(file_path):
                    return False
            
            return True
    
    def _save_progress(self, progress: Dict):
        """儲存進度到檔案"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
    
    def load_progress(self) -> Optional[Dict]:
        """加載進度檔案"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def monitor_continuously(self, interval_seconds: int = 30):
        """持續監控開發進度"""
        print("🚀 開始監控開發進度...")
        print(f"📊 總階段數: {len(self.stages)}")
        print(f"⏱️  檢查間隔: {interval_seconds}秒")
        print("-" * 50)
        
        try:
            while True:
                progress = self.check_progress()
                
                # 顯示進度
                self._display_progress(progress)
                
                # 檢查是否所有階段都已完成
                if progress['completed_stages'] >= len(self.stages):
                    print("\n🎉 所有開發階段已完成！")
                    print("✅ 功能擴展開發任務完成")
                    break
                
                # 等待下一次檢查
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n⏹️  監控已停止")
    
    def _display_progress(self, progress: Dict):
        """顯示進度資訊"""
        print(f"\n📅 {progress['timestamp']}")
        print(f"📈 進度: {progress['completed_stages']}/{progress['total_stages']} 階段")
        
        if progress['current_stage']:
            current_stage = next(
                (s for s in self.stages if s['id'] == progress['current_stage']),
                None
            )
            if current_stage:
                print(f"🔧 當前階段: {current_stage['name']}")
                print(f"   {current_stage['description']}")
        
        # 顯示階段詳情
        for stage_detail in progress['stage_details']:
            status = "✅" if stage_detail['completed'] else "⏳"
            print(f"{status} {stage_detail['name']}")
            
            if not stage_detail['completed'] and stage_detail['files_missing']:
                print(f"   缺少檔案: {', '.join(stage_detail['files_missing'][:3])}")
                if len(stage_detail['files_missing']) > 3:
                    print(f"   還有 {len(stage_detail['files_missing']) - 3} 個檔案...")
        
        print("-" * 50)
    
    def send_acceleration_command(self):
        """發送加速命令給子代理"""
        # 這裡可以實現發送命令給子代理的邏輯
        # 目前先記錄到日誌
        acceleration_log = os.path.join(self.workspace_path, 'acceleration-commands.log')
        
        command = {
            'timestamp': datetime.now().isoformat(),
            'command': 'ACCELERATE_DEVELOPMENT',
            'message': '完成當前階段後立即進行下一階段，跳過所有等待時間'
        }
        
        with open(acceleration_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(command) + '\n')
        
        print("⚡ 已發送加速開發命令")
        return True


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='開發進度監控工具')
    parser.add_argument('--monitor', action='store_true', help='持續監控模式')
    parser.add_argument('--check', action='store_true', help='單次檢查進度')
    parser.add_argument('--accelerate', action='store_true', help='發送加速命令')
    parser.add_argument('--interval', type=int, default=30, help='監控間隔（秒）')
    
    args = parser.parse_args()
    
    monitor = DevelopmentMonitor()
    
    if args.monitor:
        monitor.monitor_continuously(args.interval)
    elif args.check:
        progress = monitor.check_progress()
        monitor._display_progress(progress)
    elif args.accelerate:
        monitor.send_acceleration_command()
    else:
        # 預設顯示幫助
        progress = monitor.check_progress()
        monitor._display_progress(progress)
        print("\n可用命令:")
        print("  --monitor   持續監控模式")
        print("  --check     單次檢查進度")
        print("  --accelerate 發送加速命令")
        print("  --interval  設定監控間隔（預設30秒）")


if __name__ == '__main__':
    main()