#!/usr/bin/env python3
"""
議題系統技能 - OpenClaw 整合檔案
這個檔案讓 OpenClaw 能夠載入和使用議題系統技能
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Callable

# 添加技能目錄到路徑
skill_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, skill_dir)

from main import get_skill

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IssueSystemOpenClawIntegration:
    """議題系統 OpenClaw 整合類別"""
    
    def __init__(self):
        self.skill = None
        self.initialized = False
        self.skill_info = None
        
        logger.info("初始化議題系統 OpenClaw 整合")
    
    def initialize(self) -> bool:
        """初始化整合"""
        try:
            self.skill = get_skill()
            
            if not self.skill.initialize():
                logger.error("技能初始化失敗")
                return False
            
            self.skill_info = self.skill.get_skill_info()
            self.initialized = True
            
            logger.info(f"議題系統技能載入成功: {self.skill_info['name']} v{self.skill_info['version']}")
            return True
            
        except Exception as e:
            logger.error(f"初始化整合時發生錯誤: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """取得技能資訊（OpenClaw 標準介面）"""
        if not self.initialized:
            return {
                'name': '議題追蹤系統',
                'version': '1.0.0',
                'description': '智慧議題追蹤與管理系統（未初始化）',
                'initialized': False
            }
        
        return self.skill_info
    
    def handle_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理訊息（OpenClaw 標準介面）"""
        if not self.initialized:
            return {
                'success': False,
                'message': '議題系統未初始化',
                'error': 'NOT_INITIALIZED'
            }
        
        try:
            # 檢查是否為命令
            if message.startswith('/'):
                return self._handle_command(message, context)
            else:
                return self.skill.process_message(message, context)
                
        except Exception as e:
            logger.error(f"處理訊息時發生錯誤: {e}")
            return {
                'success': False,
                'message': f'處理訊息時發生錯誤: {str(e)}',
                'error': 'MESSAGE_HANDLING_ERROR'
            }
    
    def _handle_command(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理命令"""
        # 解析命令
        parts = message.strip().split()
        if not parts:
            return {
                'success': False,
                'message': '無效的命令格式',
                'error': 'INVALID_COMMAND'
            }
        
        command = parts[0][1:]  # 移除斜線
        args = parts[1:] if len(parts) > 1 else []
        
        # 處理議題相關命令
        if command in ['issue', '議題']:
            return self.skill.handle_command('issue', args, context)
        elif command in ['issuehistory', 'issueHistory', '議題歷史']:
            return self.skill.handle_command('issuehistory', args, context)
        elif command.startswith('issue_'):
            return self.skill.handle_command(command, args, context)
        else:
            # 不是議題系統的命令，返回空結果讓其他技能處理
            return {
                'success': True,
                'message': '',
                'buttons': [],
                'metadata': {'handled_by_other': True}
            }
    
    def handle_callback(self, callback_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理 callback query（OpenClaw 標準介面）"""
        if not self.initialized:
            return {
                'success': False,
                'message': '議題系統未初始化',
                'error': 'NOT_INITIALIZED'
            }
        
        return self.skill.handle_callback(callback_data, context)
    
    def get_commands(self) -> List[Dict[str, str]]:
        """取得支援的命令列表（OpenClaw 標準介面）"""
        if not self.initialized:
            return []
        
        return self.skill_info.get('commands', [])
    
    def get_capabilities(self) -> List[str]:
        """取得技能功能列表（OpenClaw 標準介面）"""
        if not self.initialized:
            return []
        
        return self.skill_info.get('capabilities', [])
    
    def get_status(self) -> Dict[str, Any]:
        """取得技能狀態（OpenClaw 標準介面）"""
        if not self.initialized:
            return {
                'initialized': False,
                'status': '未初始化',
                'error': 'Skill not initialized'
            }
        
        return self.skill.get_system_status()


# 全域實例
integration_instance = None

def get_integration():
    """取得整合實例（OpenClaw 標準介面）"""
    global integration_instance
    if integration_instance is None:
        integration_instance = IssueSystemOpenClawIntegration()
    return integration_instance


def register_with_openclaw() -> Dict[str, Any]:
    """註冊到 OpenClaw（主入口點）"""
    logger.info("註冊議題系統技能到 OpenClaw")
    
    integration = get_integration()
    
    if not integration.initialize():
        return {
            'success': False,
            'message': '議題系統技能初始化失敗',
            'error': 'INITIALIZATION_FAILED'
        }
    
    # 返回註冊資訊
    return {
        'success': True,
        'message': '議題系統技能註冊成功',
        'skill_info': integration.get_info(),
        'handler': integration.handle_message,
        'callback_handler': integration.handle_callback,
        'commands': integration.get_commands(),
        'capabilities': integration.get_capabilities()
    }


def test_integration():
    """測試 OpenClaw 整合"""
    print("=== 測試 OpenClaw 整合 ===\n")
    
    # 註冊技能
    print("1. 註冊技能到 OpenClaw...")
    result = register_with_openclaw()
    
    if not result['success']:
        print(f"❌ 註冊失敗: {result.get('message', '未知錯誤')}")
        return
    
    print("✅ 註冊成功")
    print()
    
    # 顯示技能資訊
    print("2. 技能資訊:")
    skill_info = result['skill_info']
    print(f"名稱: {skill_info['name']}")
    print(f"版本: {skill_info['version']}")
    print(f"描述: {skill_info['description']}")
    print(f"作者: {skill_info['author']}")
    print()
    
    # 顯示支援的命令
    print("3. 支援的命令:")
    commands = result['commands']
    for cmd in commands:
        print(f"  /{cmd['command']} - {cmd['description']}")
    print()
    
    # 顯示功能
    print("4. 功能:")
    capabilities = result['capabilities']
    for cap in capabilities:
        print(f"  • {cap}")
    print()
    
    # 測試訊息處理
    print("5. 測試訊息處理:")
    integration = get_integration()
    
    test_context = {
        'user_id': 'test_user_123',
        'chat_id': 'test_chat_456',
        'message_id': 'test_msg_789',
        'platform': 'telegram'
    }
    
    # 測試 /issue 命令
    print("  a) 測試 /issue 命令:")
    result1 = integration.handle_message('/issue', test_context)
    print(f"    成功: {result1['success']}")
    print(f"    訊息長度: {len(result1.get('message', ''))}")
    print(f"    按鈕數量: {len(result1.get('buttons', []))}")
    print()
    
    # 測試一般訊息
    print("  b) 測試一般訊息:")
    result2 = integration.handle_message('我們來討論網站SEO優化', test_context)
    print(f"    成功: {result2['success']}")
    print(f"    需要回覆: {not result2.get('metadata', {}).get('no_reply', False)}")
    if result2.get('message'):
        print(f"    訊息: {result2['message'][:50]}...")
    print()
    
    # 測試系統狀態
    print("6. 系統狀態:")
    status = integration.get_status()
    print(f"    成功: {status['success']}")
    print(f"    狀態: {status.get('status', '未知')}")
    
    if status['success'] and 'data' in status:
        data = status['data']
        print(f"    議題總數: {data.get('total_issues', 0)}")
        print(f"    開啟議題: {data.get('open_issues', 0)}")
        print(f"    關閉議題: {data.get('closed_issues', 0)}")
    
    print("\n✅ OpenClaw 整合測試完成")


if __name__ == "__main__":
    test_integration()