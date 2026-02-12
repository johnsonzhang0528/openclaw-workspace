#!/usr/bin/env python3
"""
配置管理模組
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SkillConfig:
    """技能配置管理"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置
        
        Args:
            config_path: 配置檔案路徑
        """
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        
        # 技能信息
        self.skill_name = "{{skill_name}}"
        self.version = "1.0.0"
        self.author = "{{author}}"
        self.description = "{{description}}"
        
        # 從 package.json 加載技能信息
        self._load_package_info()
    
    def _find_config_path(self) -> str:
        """查找配置檔案路徑"""
        # 可能的配置檔案位置
        possible_paths = [
            os.path.join(os.path.expanduser('~'), '.openclaw', 'openclaw.json'),
            '/etc/openclaw/openclaw.json',
            '/usr/local/etc/openclaw/openclaw.json'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果找不到，使用預設路徑
        default_path = os.path.join(
            os.path.expanduser('~'), '.openclaw', 'openclaw.json'
        )
        return default_path
    
    def _load_config(self) -> Dict[str, Any]:
        """加載配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"配置檔案不存在: {self.config_path}")
                return self._create_default_config()
        except Exception as e:
            logger.error(f"加載配置失敗: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """創建預設配置"""
        return {
            "skills": {
                "{{skill_name}}": {
                    "enabled": True,
                    "config": {
                        "telegram_enabled": True,
                        "data_path": os.path.join(
                            os.path.expanduser('~'),
                            '.openclaw',
                            'workspace',
                            '{{skill_name}}'
                        )
                    }
                }
            }
        }
    
    def _load_package_info(self):
        """從 package.json 加載技能信息"""
        package_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'package.json'
        )
        
        if os.path.exists(package_path):
            try:
                with open(package_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    
                    self.skill_name = package_data.get('name', self.skill_name)
                    self.version = package_data.get('version', self.version)
                    self.author = package_data.get('author', self.author)
                    self.description = package_data.get('description', self.description)
                    
                    # 加載 OpenClaw 特定配置
                    openclaw_config = package_data.get('openclaw', {})
                    if openclaw_config:
                        self.category = openclaw_config.get('category', 'utility')
            except Exception as e:
                logger.error(f"加載 package.json 失敗: {e}")
    
    def get_skill_config(self) -> Dict[str, Any]:
        """獲取技能配置"""
        return self.config.get('skills', {}).get('{{skill_name}}', {}).get('config', {})
    
    @property
    def enabled(self) -> bool:
        """是否啟用技能"""
        return self.config.get('skills', {}).get('{{skill_name}}', {}).get('enabled', True)
    
    @property
    def telegram_enabled(self) -> bool:
        """是否啟用 Telegram 介面"""
        return self.get_skill_config().get('telegram_enabled', True)
    
    @property
    def data_path(self) -> str:
        """資料儲存路徑"""
        default_path = os.path.join(
            os.path.expanduser('~'),
            '.openclaw',
            'workspace',
            '{{skill_name}}'
        )
        return self.get_skill_config().get('data_path', default_path)
    
    def get_config_info(self) -> Dict[str, Any]:
        """獲取配置信息"""
        return {
            'enabled': self.enabled,
            'telegram_enabled': self.telegram_enabled,
            'data_path': self.data_path,
            'version': self.version,
            'skill_name': self.skill_name,
            'author': self.author,
            'description': self.description
        }
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """更新配置
        
        Args:
            updates: 更新內容
            
        Returns:
            是否成功
        """
        try:
            # 更新技能配置
            if 'skills' not in self.config:
                self.config['skills'] = {}
            
            if '{{skill_name}}' not in self.config['skills']:
                self.config['skills']['{{skill_name}}'] = {}
            
            skill_config = self.config['skills']['{{skill_name}}']
            
            # 更新配置
            for key, value in updates.items():
                if key == 'enabled':
                    skill_config['enabled'] = value
                elif key == 'config':
                    if 'config' not in skill_config:
                        skill_config['config'] = {}
                    skill_config['config'].update(value)
            
            # 儲存配置
            self._save_config()
            return True
            
        except Exception as e:
            logger.error(f"更新配置失敗: {e}")
            return False
    
    def _save_config(self):
        """儲存配置"""
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已儲存到: {self.config_path}")
            
        except Exception as e:
            logger.error(f"儲存配置失敗: {e}")
            raise


if __name__ == '__main__':
    # 測試配置模組
    config = SkillConfig()
    print(f"技能名稱: {config.skill_name}")
    print(f"版本: {config.version}")
    print(f"是否啟用: {config.enabled}")
    print(f"Telegram 啟用: {config.telegram_enabled}")
    print(f"資料路徑: {config.data_path}")