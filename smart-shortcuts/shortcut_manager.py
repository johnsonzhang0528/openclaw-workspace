#!/usr/bin/env python3
"""
快捷指令管理器
管理快捷指令的創建、讀取、更新、刪除和執行統計
"""

import asyncio
import logging
import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

from .config import Config
from .utils import validate_shortcut, format_shortcut_info, generate_shortcut_id

logger = logging.getLogger(__name__)

class ShortcutManager:
    """快捷指令管理器"""
    
    def __init__(self, config: Config):
        """初始化快捷指令管理器"""
        self.config = config
        self.shortcuts = {}
        self.categories = defaultdict(list)
        self.usage_stats = defaultdict(lambda: {"count": 0, "last_used": 0, "total_time": 0})
        self.loaded = False
        
    async def load_shortcuts(self):
        """載入快捷指令"""
        shortcuts_file = self.config.shortcuts_file
        
        try:
            if os.path.exists(shortcuts_file):
                with open(shortcuts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.shortcuts = data.get("shortcuts", {})
                self.categories = defaultdict(list)
                
                # 重建分類索引
                for name, shortcut in self.shortcuts.items():
                    category = shortcut.get("category", "uncategorized")
                    self.categories[category].append(name)
                    
                # 載入使用統計
                stats_file = self.config.stats_file
                if os.path.exists(stats_file):
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        stats_data = json.load(f)
                        self.usage_stats = defaultdict(lambda: {"count": 0, "last_used": 0, "total_time": 0}, 
                                                      stats_data.get("usage_stats", {}))
                        
                logger.info(f"載入 {len(self.shortcuts)} 個快捷指令")
                self.loaded = True
                
            else:
                logger.info("快捷指令檔案不存在，創建新檔案")
                self._create_default_shortcuts()
                await self.save_shortcuts()
                
        except Exception as e:
            logger.error(f"載入快捷指令時發生錯誤: {e}")
            self._create_default_shortcuts()
            
    async def save_shortcuts(self):
        """保存快捷指令"""
        try:
            # 準備數據
            data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "shortcuts": self.shortcuts
            }
            
            # 寫入檔案
            with open(self.config.shortcuts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            # 保存統計數據
            stats_data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "usage_stats": dict(self.usage_stats)
            }
            
            with open(self.config.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
                
            logger.debug("快捷指令已保存")
            
        except Exception as e:
            logger.error(f"保存快捷指令時發生錯誤: {e}")
            
    def _create_default_shortcuts(self):
        """創建預設快捷指令"""
        default_shortcuts = {
            "system_info": {
                "name": "系統資訊",
                "description": "顯示系統基本資訊",
                "category": "system",
                "action_type": "custom",
                "handler": "system_info",
                "tags": ["system", "info", "diagnostic"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            "list_files": {
                "name": "列出檔案",
                "description": "列出當前目錄的檔案",
                "category": "file",
                "action_type": "command",
                "command": "ls -la",
                "tags": ["file", "list", "directory"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            "disk_usage": {
                "name": "磁碟使用情況",
                "description": "顯示磁碟使用情況",
                "category": "system",
                "action_type": "command",
                "command": "df -h",
                "tags": ["system", "disk", "storage"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            "memory_info": {
                "name": "記憶體資訊",
                "description": "顯示記憶體使用情況",
                "category": "system",
                "action_type": "command",
                "command": "free -h",
                "tags": ["system", "memory", "ram"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            "process_list": {
                "name": "進程列表",
                "description": "顯示運行中的進程",
                "category": "system",
                "action_type": "command",
                "command": "ps aux | head -20",
                "tags": ["system", "process", "monitor"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        }
        
        self.shortcuts = default_shortcuts
        
        # 重建分類索引
        self.categories = defaultdict(list)
        for name, shortcut in self.shortcuts.items():
            category = shortcut.get("category", "uncategorized")
            self.categories[category].append(name)
            
        self.loaded = True
        logger.info(f"創建 {len(self.shortcuts)} 個預設快捷指令")
        
    def get_shortcut(self, name: str) -> Optional[Dict[str, Any]]:
        """獲取快捷指令"""
        return self.shortcuts.get(name)
        
    def list_shortcuts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出快捷指令"""
        if category:
            shortcut_names = self.categories.get(category, [])
            return [self.shortcuts[name] for name in shortcut_names if name in self.shortcuts]
        else:
            return list(self.shortcuts.values())
            
    async def create_shortcut(self, shortcut_data: Dict[str, Any]) -> Dict[str, Any]:
        """創建快捷指令"""
        try:
            # 驗證數據
            validation_result = validate_shortcut(shortcut_data)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
                
            name = shortcut_data.get("name")
            if not name:
                return {"success": False, "error": "快捷指令名稱不能為空"}
                
            # 檢查是否已存在
            if name in self.shortcuts:
                return {"success": False, "error": f"快捷指令 '{name}' 已存在"}
                
            # 添加元數據
            shortcut_data["created_at"] = datetime.now().isoformat()
            shortcut_data["updated_at"] = datetime.now().isoformat()
            
            # 生成ID
            if "id" not in shortcut_data:
                shortcut_data["id"] = generate_shortcut_id(shortcut_data)
                
            # 添加到管理器
            self.shortcuts[name] = shortcut_data
            
            # 更新分類索引
            category = shortcut_data.get("category", "uncategorized")
            self.categories[category].append(name)
            
            # 保存到檔案
            await self.save_shortcuts()
            
            logger.info(f"創建快捷指令: {name}")
            
            return {
                "success": True,
                "shortcut": name,
                "data": shortcut_data
            }
            
        except Exception as e:
            logger.error(f"創建快捷指令時發生錯誤: {e}")
            return {"success": False, "error": str(e)}
            
    async def update_shortcut(self, name: str, shortcut_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新快捷指令"""
        try:
            # 檢查是否存在
            if name not in self.shortcuts:
                return {"success": False, "error": f"快捷指令 '{name}' 不存在"}
                
            # 獲取原始數據
            original_shortcut = self.shortcuts[name]
            
            # 更新數據
            updated_shortcut = {**original_shortcut, **shortcut_data}
            updated_shortcut["updated_at"] = datetime.now().isoformat()
            
            # 驗證數據
            validation_result = validate_shortcut(updated_shortcut)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
                
            # 檢查分類是否變更
            old_category = original_shortcut.get("category", "uncategorized")
            new_category = updated_shortcut.get("category", "uncategorized")
            
            if old_category != new_category:
                # 從舊分類移除
                if name in self.categories[old_category]:
                    self.categories[old_category].remove(name)
                    
                # 添加到新分類
                self.categories[new_category].append(name)
                
            # 更新管理器
            self.shortcuts[name] = updated_shortcut
            
            # 保存到檔案
            await self.save_shortcuts()
            
            logger.info(f"更新快捷指令: {name}")
            
            return {
                "success": True,
                "shortcut": name,
                "data": updated_shortcut
            }
            
        except Exception as e:
            logger.error(f"更新快捷指令時發生錯誤: {e}")
            return {"success": False, "error": str(e)}
            
    async def delete_shortcut(self, name: str) -> Dict[str, Any]:
        """刪除快捷指令"""
        try:
            # 檢查是否存在
            if name not in self.shortcuts:
                return {"success": False, "error": f"快捷指令 '{name}' 不存在"}
                
            # 從分類索引中移除
            shortcut = self.shortcuts[name]
            category = shortcut.get("category", "uncategorized")
            
            if name in self.categories[category]:
                self.categories[category].remove(name)
                
            # 從管理器中移除
            del self.shortcuts[name]
            
            # 從統計中移除
            if name in self.usage_stats:
                del self.usage_stats[name]
                
            # 保存到檔案
            await self.save_shortcuts()
            
            logger.info(f"刪除快捷指令: {name}")
            
            return {
                "success": True,
                "shortcut": name,
                "message": f"快捷指令 '{name}' 已刪除"
            }
            
        except Exception as e:
            logger.error(f"刪除快捷指令時發生錯誤: {e}")
            return {"success": False, "error": str(e)}
            
    def record_usage(self, shortcut_name: str, execution_time: float = 0):
        """記錄使用統計"""
        if shortcut_name not in self.usage_stats:
            self.usage_stats[shortcut_name] = {"count": 0, "last_used": 0, "total_time": 0}
            
        stats = self.usage_stats[shortcut_name]
        stats["count"] += 1
        stats["last_used"] = time.time()
        stats["total_time"] += execution_time
        
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計數據"""
        total_shortcuts = len(self.shortcuts)
        total_categories = len(self.categories)
        
        # 計算使用統計
        total_usage = sum(stats["count"] for stats in self.usage_stats.values())
        most_used = None
        most_used_count = 0
        
        for name, stats in self.usage_stats.items():
            if stats["count"] > most_used_count:
                most_used_count = stats["count"]
                most_used = name
                
        # 計算分類統計
        category_stats = {}
        for category, shortcuts in self.categories.items():
            category_stats[category] = {
                "count": len(shortcuts),
                "shortcuts": shortcuts[:5]  # 只顯示前5個
            }
            
        return {
            "total_shortcuts": total_shortcuts,
            "total_categories": total_categories,
            "total_usage": total_usage,
            "most_used": {
                "name": most_used,
                "count": most_used_count
            } if most_used else None,
            "category_stats": category_stats,
            "recently_used": self.get_recently_used(limit=10)
        }
        
    def get_recently_used(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近使用的快捷指令"""
        # 按最後使用時間排序
        sorted_stats = sorted(
            self.usage_stats.items(),
            key=lambda x: x[1]["last_used"],
            reverse=True
        )
        
        result = []
        for name, stats in sorted_stats[:limit]:
            shortcut = self.shortcuts.get(name)
            if shortcut:
                result.append({
                    "name": name,
                    "count": stats["count"],
                    "last_used": stats["last_used"],
                    "last_used_formatted": datetime.fromtimestamp(stats["last_used"]).strftime("%Y-%m-%d %H:%M:%S") if stats["last_used"] > 0 else "從未使用",
                    "description": shortcut.get("description", ""),
                    "category": shortcut.get("category", "uncategorized")
                })
                
        return result
        
    def search_shortcuts(self, query: str, search_fields: List[str] = None) -> List[Dict[str, Any]]:
        """搜尋快捷指令"""
        if not query:
            return []
            
        if search_fields is None:
            search_fields = ["name", "description", "tags", "command"]
            
        query_lower = query.lower()
        results = []
        
        for name, shortcut in self.shortcuts.items():
            for field in search_fields:
                if field in shortcut:
                    field_value = shortcut[field]
                    
                    # 處理不同類型的字段
                    if isinstance(field_value, str):
                        if query_lower in field_value.lower():
                            results.append(shortcut)
                            break
                    elif isinstance(field_value, list):
                        # 檢查列表中的每個項目
                        for item in field_value:
                            if isinstance(item, str) and query_lower in item.lower():
                                results.append(shortcut)
                                break
                                
        return results
        
    def export_shortcuts(self, format: str = "json") -> str:
        """導出快捷指令"""
        if format == "json":
            return json.dumps({
                "shortcuts": self.shortcuts,
                "exported_at": datetime.now().isoformat(),
                "count": len(self.shortcuts)
            }, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支援的導出格式: {format}")
            
    async def import_shortcuts(self, data: str, format: str = "json", merge: bool = True) -> Dict[str, Any]:
        """導入快捷指令"""
        try:
            if format == "json":
                imported_data = json.loads(data)
                imported_shortcuts = imported_data.get("shortcuts", {})
                
                imported_count = 0
                skipped_count = 0
                updated_count = 0
                
                for name, shortcut in imported_shortcuts.items():
                    if name in self.shortcuts:
                        if merge:
                            # 合併現有快捷指令
                            await self.update_shortcut(name, shortcut)
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        # 創建新快捷指令
                        await self.create_shortcut(shortcut)
                        imported_count += 1
                        
                # 保存更改
                await self.save_shortcuts()
                
                return {
                    "success": True,
                    "imported": imported_count,
                    "updated": updated_count,
                    "skipped": skipped_count,
                    "total": len(self.shortcuts)
                }
            else:
                return {"success": False, "error": f"不支援的導入格式: {format}"}
                
        except Exception as e:
            logger.error(f"導入快捷指令時發生錯誤: {e}")
            return {"success": False, "error": str(e)}
            
    def get_status(self) -> Dict[str, Any]:
        """獲取管理器狀態"""
        return {
            "loaded": self.loaded,
            "shortcuts_count": len(self.shortcuts),
            "categories_count": len(self.categories),
            "usage_stats_count": len(self.usage_stats),
            "config": self.config.get_summary()
        }