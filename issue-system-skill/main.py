#!/usr/bin/env python3
"""
議題系統技能 - OpenClaw 技能主程式
提供完整的 Telegram 議題互動介面
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

# 添加工作空間路徑
workspace_path = '/root/.openclaw/workspace'
sys.path.insert(0, workspace_path)

# 嘗試載入議題系統模組
try:
    from issue_telegram_integration import get_telegram_integration
    HAS_ISSUE_SYSTEM = True
except ImportError as e:
    logging.error(f"無法載入議題系統模組: {e}")
    HAS_ISSUE_SYSTEM = False

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IssueSystemSkill:
    """議題系統技能主類別"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化技能"""
        self.version = "1.0.0"
        self.name = "議題追蹤系統"
        self.description = "智慧議題追蹤與管理系統，提供 Telegram 互動介面"
        self.author = "OpenClaw"
        
        self.initialized = False
        self.integration = None
        
        logger.info(f"初始化 {self.name} v{self.version}")
    
    def initialize(self) -> bool:
        """初始化技能，返回是否成功"""
        try:
            if not HAS_ISSUE_SYSTEM:
                logger.error("議題系統模組未載入")
                return False
            
            # 初始化 Telegram 整合
            self.integration = get_telegram_integration()
            
            self.initialized = True
            logger.info(f"{self.name} 初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化失敗: {e}")
            return False
    
    def handle_command(self, command: str, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理 OpenClaw 命令
        
        Args:
            command: 命令名稱
            args: 命令參數
            context: 上下文資訊
            
        Returns:
            回應字典，格式為 OpenClaw 標準格式
        """
        if not self.initialized:
            return {
                'success': False,
                'message': '議題系統技能未初始化',
                'error': 'NOT_INITIALIZED'
            }
        
        try:
            # 檢查是否為議題相關命令
            if command in ['issue', '議題']:
                return self._handle_issue_command(args, context)
            elif command in ['issuehistory', '議題歷史']:
                return self._handle_issue_history_command(args, context)
            elif command.startswith('issue_'):
                return self._handle_issue_action_command(command, args, context)
            else:
                return {
                    'success': False,
                    'message': f'未知命令: {command}',
                    'error': 'UNKNOWN_COMMAND'
                }
                
        except Exception as e:
            logger.error(f"處理命令時發生錯誤: {e}")
            return {
                'success': False,
                'message': f'處理命令時發生錯誤: {str(e)}',
                'error': 'COMMAND_ERROR'
            }
    
    def _handle_issue_command(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理 /issue 命令"""
        try:
            # 使用 Telegram 整合處理命令
            result = self.integration.handle_telegram_command("/issue")
            
            # 轉換為 OpenClaw 格式
            return self._convert_to_openclaw_format(result, context)
            
        except Exception as e:
            logger.error(f"處理 /issue 命令時發生錯誤: {e}")
            return {
                'success': False,
                'message': f'處理議題列表時發生錯誤: {str(e)}',
                'error': 'ISSUE_LIST_ERROR'
            }
    
    def _handle_issue_history_command(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理 /issueHistory 命令"""
        try:
            result = self.integration.handle_telegram_command("/issueHistory")
            return self._convert_to_openclaw_format(result, context)
            
        except Exception as e:
            logger.error(f"處理 /issueHistory 命令時發生錯誤: {e}")
            return {
                'success': False,
                'message': f'處理議題歷史時發生錯誤: {str(e)}',
                'error': 'ISSUE_HISTORY_ERROR'
            }
    
    def _handle_issue_action_command(self, command: str, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理議題操作命令"""
        try:
            # 將 OpenClaw 命令格式轉換為 Telegram 命令格式
            telegram_command = f"/{command.replace('_', '_', 1)}"
            
            # 如果有參數，添加到命令中
            if args:
                telegram_command += f"_{args[0]}"
            
            result = self.integration.handle_telegram_command(telegram_command)
            return self._convert_to_openclaw_format(result, context)
            
        except Exception as e:
            logger.error(f"處理議題操作命令時發生錯誤: {e}")
            return {
                'success': False,
                'message': f'處理議題操作時發生錯誤: {str(e)}',
                'error': 'ISSUE_ACTION_ERROR'
            }
    
    def handle_callback(self, callback_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理 callback query（按鈕點擊）"""
        if not self.initialized:
            return {
                'success': False,
                'message': '議題系統技能未初始化',
                'error': 'NOT_INITIALIZED'
            }
        
        try:
            result = self.integration.handle_callback_query(callback_data)
            return self._convert_to_openclaw_format(result, context)
            
        except Exception as e:
            logger.error(f"處理 callback 時發生錯誤: {e}")
            return {
                'success': False,
                'message': f'處理按鈕點擊時發生錯誤: {str(e)}',
                'error': 'CALLBACK_ERROR'
            }
    
    def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """處理一般訊息，自動偵測議題"""
        if not self.initialized:
            return {
                'success': False,
                'message': '議題系統技能未初始化',
                'error': 'NOT_INITIALIZED'
            }
        
        try:
            result = self.integration.process_message_for_telegram(message)
            
            # 如果不需要回覆，返回空結果
            if not result.get('text'):
                return {
                    'success': True,
                    'message': '',
                    'buttons': [],
                    'metadata': {'no_reply': True}
                }
            
            return self._convert_to_openclaw_format(result, context)
            
        except Exception as e:
            logger.error(f"處理訊息時發生錯誤: {e}")
            return {
                'success': False,
                'message': f'處理訊息時發生錯誤: {str(e)}',
                'error': 'MESSAGE_ERROR'
            }
    
    def _convert_to_openclaw_format(self, telegram_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """將 Telegram 結果轉換為 OpenClaw 格式"""
        openclaw_result = {
            'success': True,
            'message': telegram_result.get('text', ''),
            'buttons': telegram_result.get('buttons', []),
            'metadata': {
                'parse_mode': telegram_result.get('parse_mode', 'Markdown'),
                'edit_message': telegram_result.get('edit', False),
                'skill': self.name,
                'version': self.version
            }
        }
        
        # 添加上下文資訊
        if context:
            openclaw_result['metadata']['context'] = {
                'user_id': context.get('user_id'),
                'chat_id': context.get('chat_id'),
                'message_id': context.get('message_id'),
                'platform': context.get('platform', 'telegram')
            }
        
        return openclaw_result
    
    def get_skill_info(self) -> Dict[str, Any]:
        """取得技能資訊"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'commands': [
                {
                    'command': 'issue',
                    'description': '查看當前議題列表',
                    'usage': '/issue'
                },
                {
                    'command': 'issuehistory',
                    'description': '查看歷史議題',
                    'usage': '/issueHistory'
                }
            ],
            'capabilities': [
                'telegram_inline_keyboard',
                'issue_detection',
                'issue_management',
                'automatic_summarization'
            ],
            'initialized': self.initialized,
            'has_issue_system': HAS_ISSUE_SYSTEM
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態"""
        try:
            if self.integration:
                status_result = self.integration.get_system_status()
                return {
                    'success': True,
                    'status': status_result['status'],
                    'data': status_result.get('data', {}),
                    'skill_info': self.get_skill_info()
                }
            else:
                return {
                    'success': False,
                    'status': '未初始化',
                    'error': 'Integration not available'
                }
        except Exception as e:
            return {
                'success': False,
                'status': '錯誤',
                'error': str(e)
            }


# 全域實例
issue_system_skill = None

def get_skill():
    """取得技能實例（OpenClaw 標準介面）"""
    global issue_system_skill
    if issue_system_skill is None:
        issue_system_skill = IssueSystemSkill()
    return issue_system_skill


def test_skill():
    """測試技能功能"""
    print("=== 測試議題系統技能 ===\n")
    
    skill = get_skill()
    
    # 初始化技能
    print("1. 初始化技能...")
    if skill.initialize():
        print("✅ 技能初始化成功")
    else:
        print("❌ 技能初始化失敗")
        return
    
    print()
    
    # 測試技能資訊
    print("2. 技能資訊:")
    info = skill.get_skill_info()
    print(f"名稱: {info['name']}")
    print(f"版本: {info['version']}")
    print(f"描述: {info['description']}")
    print(f"命令數量: {len(info['commands'])}")
    print(f"功能: {', '.join(info['capabilities'])}")
    print()
    
    # 測試 /issue 命令
    print("3. 測試 /issue 命令:")
    context = {
        'user_id': 'test_user',
        'chat_id': 'test_chat',
        'message_id': 'test_msg',
        'platform': 'telegram'
    }
    
    result = skill.handle_command('issue', [], context)
    print(f"成功: {result['success']}")
    print(f"訊息長度: {len(result.get('message', ''))}")
    print(f"按鈕數量: {len(result.get('buttons', []))}")
    print()
    
    # 測試系統狀態
    print("4. 系統狀態:")
    status = skill.get_system_status()
    print(f"成功: {status['success']}")
    print(f"狀態: {status.get('status', '未知')}")
    if status['success'] and 'data' in status:
        data = status['data']
        print(f"議題總數: {data.get('total_issues', 0)}")
        print(f"開啟議題: {data.get('open_issues', 0)}")
        print(f"關閉議題: {data.get('closed_issues', 0)}")
    
    print("\n✅ 技能測試完成")


if __name__ == "__main__":
    test_skill()