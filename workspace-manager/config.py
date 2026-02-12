#!/usr/bin/env python3
"""
工作空間管理工具 - 配置管理
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SkillConfig:
    """技能配置類別"""
    
    # 基本配置
    version: str = "2.0.0"
    skill_name: str = "workspace-manager"
    
    # 路徑配置
    skill_dir: str = field(default_factory=lambda: os.path.dirname(os.path.abspath(__file__)))
    workspace_root: str = "/root/.openclaw/workspace"
    data_path: str = field(init=False)
    cache_path: str = field(init=False)
    backup_path: str = field(init=False)
    
    # 檔案操作配置
    max_file_size: int = 10485760  # 10MB
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ".txt", ".md", ".py", ".js", ".json", ".yaml", ".yml",
        ".html", ".css", ".xml", ".csv", ".log", ".ini", ".cfg",
        ".sh", ".bash", ".zsh", ".sql", ".java", ".cpp", ".c", ".h",
        ".go", ".rs", ".php", ".rb", ".pl", ".lua", ".r", ".m", ".swift"
    ])
    
    # 搜尋配置
    search_history_size: int = 50
    enable_content_search: bool = True
    max_search_results: int = 100
    
    # 顯示配置
    items_per_page: int = 20
    enable_thumbnails: bool = True
    thumbnail_size: tuple = (64, 64)
    theme: str = "dark"  # dark, light, auto
    
    # 安全配置
    backup_enabled: bool = True
    trash_enabled: bool = True
    protected_files: List[str] = field(default_factory=lambda: [
        ".env", "config.json", "secrets.json", "credentials.json",
        "private.key", "id_rsa", "id_dsa"
    ])
    
    # Telegram 配置
    telegram_enabled: bool = True
    telegram_timeout: int = 30
    
    # 書籤配置
    default_bookmarks: List[str] = field(default_factory=lambda: [
        "/root/.openclaw/workspace",
        "/root/.openclaw/logs",
        "/root/.openclaw/config",
        "/root/.openclaw/skills"
    ])
    
    def __post_init__(self):
        """初始化後處理"""
        # 設置路徑
        self.data_path = os.path.join(self.skill_dir, "data")
        self.cache_path = os.path.join(self.data_path, "cache")
        self.backup_path = os.path.join(self.data_path, "backups")
        
        # 確保目錄存在
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.cache_path, exist_ok=True)
        os.makedirs(self.backup_path, exist_ok=True)
    
    @classmethod
    def from_file(cls, config_path: Optional[str] = None) -> 'SkillConfig':
        """從檔案加載配置"""
        config = cls()
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 更新配置
                for key, value in user_config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                
                logger.info(f"從 {config_path} 加載配置")
            except Exception as e:
                logger.error(f"加載配置失敗: {e}")
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return asdict(self)
    
    def save(self, config_path: str) -> bool:
        """保存配置到檔案"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到 {config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置失敗: {e}")
            return False
    
    def get_workspace_path(self, path: str = "") -> str:
        """獲取工作空間內的完整路徑"""
        if os.path.isabs(path):
            # 確保路徑在工作空間內
            if not path.startswith(self.workspace_root):
                raise ValueError(f"路徑 {path} 不在工作空間內")
            return path
        else:
            return os.path.join(self.workspace_root, path)
    
    def is_allowed_file(self, filepath: str) -> bool:
        """檢查檔案是否允許訪問"""
        try:
            # 檢查是否在工作空間內
            abs_path = os.path.abspath(filepath)
            if not abs_path.startswith(self.workspace_root):
                return False
            
            # 檢查檔案大小
            if os.path.getsize(filepath) > self.max_file_size:
                return False
            
            # 檢查副檔名
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in self.allowed_extensions:
                return False
            
            # 檢查是否為受保護檔案
            filename = os.path.basename(filepath)
            if filename in self.protected_files:
                return False
            
            return True
        except Exception:
            return False
    
    def get_cache_file(self, cache_name: str) -> str:
        """獲取快取檔案路徑"""
        return os.path.join(self.cache_path, f"{cache_name}.json")
    
    def get_backup_file(self, original_path: str) -> str:
        """獲取備份檔案路徑"""
        import time
        timestamp = int(time.time())
        filename = os.path.basename(original_path)
        backup_name = f"{filename}.{timestamp}.bak"
        return os.path.join(self.backup_path, backup_name)


# 預設配置實例
default_config = SkillConfig()