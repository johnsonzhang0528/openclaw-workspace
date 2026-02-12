#!/usr/bin/env python3
"""
檔案瀏覽器模組 - 提供樹狀目錄導覽和檔案瀏覽功能
"""

import os
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FileType(Enum):
    """檔案類型枚舉"""
    DIRECTORY = "directory"
    FILE = "file"
    SYMLINK = "symlink"
    UNKNOWN = "unknown"


@dataclass
class FileInfo:
    """檔案資訊類別"""
    name: str
    path: str
    type: FileType
    size: int = 0
    modified: float = 0
    permissions: str = ""
    extension: str = ""
    is_hidden: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type.value,
            "size": self.size,
            "modified": self.modified,
            "permissions": self.permissions,
            "extension": self.extension,
            "is_hidden": self.is_hidden,
            "size_human": self._format_size(),
            "modified_human": self._format_time()
        }
    
    def _format_size(self) -> str:
        """格式化檔案大小"""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.1f} GB"
    
    def _format_time(self) -> str:
        """格式化修改時間"""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.modified))


class FileBrowser:
    """檔案瀏覽器類別"""
    
    def __init__(self, config):
        """初始化檔案瀏覽器"""
        self.config = config
        self.cache = {}
        self.cache_ttl = 300  # 5分鐘快取
        
    def list_directory(self, path: str, show_hidden: bool = False, 
                      sort_by: str = "name", reverse: bool = False) -> List[FileInfo]:
        """列出目錄內容"""
        try:
            abs_path = self.config.get_workspace_path(path)
            
            # 檢查目錄是否存在
            if not os.path.exists(abs_path):
                raise FileNotFoundError(f"目錄不存在: {path}")
            
            if not os.path.isdir(abs_path):
                raise NotADirectoryError(f"不是目錄: {path}")
            
            # 獲取目錄內容
            items = []
            for item_name in os.listdir(abs_path):
                item_path = os.path.join(abs_path, item_name)
                
                # 檢查是否隱藏檔案
                is_hidden = item_name.startswith('.')
                if not show_hidden and is_hidden:
                    continue
                
                # 獲取檔案資訊
                file_info = self._get_file_info(item_path, item_name)
                if file_info:
                    items.append(file_info)
            
            # 排序
            items = self._sort_items(items, sort_by, reverse)
            
            return items
            
        except Exception as e:
            logger.error(f"列出目錄失敗: {e}")
            raise
    
    def _get_file_info(self, filepath: str, name: str) -> Optional[FileInfo]:
        """獲取檔案資訊"""
        try:
            stat = os.stat(filepath)
            
            # 判斷檔案類型
            if os.path.isdir(filepath):
                file_type = FileType.DIRECTORY
            elif os.path.isfile(filepath):
                file_type = FileType.FILE
            elif os.path.islink(filepath):
                file_type = FileType.SYMLINK
            else:
                file_type = FileType.UNKNOWN
            
            # 獲取副檔名
            extension = os.path.splitext(name)[1].lower() if file_type == FileType.FILE else ""
            
            # 獲取權限
            permissions = oct(stat.st_mode)[-3:]
            
            return FileInfo(
                name=name,
                path=filepath,
                type=file_type,
                size=stat.st_size if file_type == FileType.FILE else 0,
                modified=stat.st_mtime,
                permissions=permissions,
                extension=extension,
                is_hidden=name.startswith('.')
            )
            
        except Exception as e:
            logger.error(f"獲取檔案資訊失敗 {filepath}: {e}")
            return None
    
    def _sort_items(self, items: List[FileInfo], sort_by: str, reverse: bool) -> List[FileInfo]:
        """排序項目"""
        if sort_by == "name":
            return sorted(items, key=lambda x: x.name.lower(), reverse=reverse)
        elif sort_by == "size":
            return sorted(items, key=lambda x: x.size, reverse=reverse)
        elif sort_by == "modified":
            return sorted(items, key=lambda x: x.modified, reverse=reverse)
        elif sort_by == "type":
            return sorted(items, key=lambda x: (x.type.value, x.name.lower()), reverse=reverse)
        else:
            return items
    
    def get_directory_tree(self, path: str, max_depth: int = 3, 
                          current_depth: int = 0) -> Dict[str, Any]:
        """獲取目錄樹狀結構"""
        try:
            abs_path = self.config.get_workspace_path(path)
            
            if not os.path.isdir(abs_path):
                return {"name": os.path.basename(abs_path), "type": "file", "path": abs_path}
            
            # 緩存檢查
            cache_key = f"tree_{abs_path}_{max_depth}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    return cached_data
            
            # 構建樹狀結構
            tree = {
                "name": os.path.basename(abs_path) or "/",
                "type": "directory",
                "path": abs_path,
                "children": []
            }
            
            if current_depth >= max_depth:
                return tree
            
            try:
                for item_name in os.listdir(abs_path):
                    item_path = os.path.join(abs_path, item_name)
                    
                    if os.path.isdir(item_path):
                        # 遞歸處理子目錄
                        child_tree = self.get_directory_tree(
                            item_path, max_depth, current_depth + 1
                        )
                        tree["children"].append(child_tree)
                    else:
                        # 檔案節點
                        tree["children"].append({
                            "name": item_name,
                            "type": "file",
                            "path": item_path
                        })
            except PermissionError:
                logger.warning(f"無權限訪問目錄: {abs_path}")
            
            # 緩存結果
            self.cache[cache_key] = (tree, time.time())
            
            return tree
            
        except Exception as e:
            logger.error(f"獲取目錄樹失敗: {e}")
            return {"name": "error", "type": "error", "path": path, "error": str(e)}
    
    def get_file_preview(self, filepath: str, max_lines: int = 20) -> Dict[str, Any]:
        """獲取檔案預覽"""
        try:
            abs_path = self.config.get_workspace_path(filepath)
            
            if not os.path.isfile(abs_path):
                raise FileNotFoundError(f"不是檔案: {filepath}")
            
            # 檢查檔案大小
            file_size = os.path.getsize(abs_path)
            if file_size > self.config.max_file_size:
                return {
                    "success": False,
                    "error": f"檔案太大 ({file_size} bytes)，超過限制 {self.config.max_file_size} bytes"
                }
            
            # 檢查副檔名
            ext = os.path.splitext(abs_path)[1].lower()
            if ext not in self.config.allowed_extensions:
                return {
                    "success": False,
                    "error": f"不支援的檔案類型: {ext}"
                }
            
            # 讀取檔案內容
            content = self._read_file_content(abs_path, max_lines)
            
            return {
                "success": True,
                "path": abs_path,
                "size": file_size,
                "lines": len(content.splitlines()),
                "preview": content,
                "encoding": "utf-8"
            }
            
        except Exception as e:
            logger.error(f"獲取檔案預覽失敗: {e}")
            return {"success": False, "error": str(e)}
    
    def _read_file_content(self, filepath: str, max_lines: int) -> str:
        """讀取檔案內容"""
        try:
            # 嘗試 UTF-8 編碼
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... (總共 {i+1} 行，顯示前 {max_lines} 行)")
                        break
                    lines.append(line.rstrip('\n'))
                return '\n'.join(lines)
        except UnicodeDecodeError:
            # 嘗試其他編碼
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            lines.append(f"... (總共 {i+1} 行，顯示前 {max_lines} 行)")
                            break
                        lines.append(line.rstrip('\n'))
                    return '\n'.join(lines)
            except Exception:
                return "[二進位檔案或未知編碼]"
    
    def get_directory_stats(self, path: str) -> Dict[str, Any]:
        """獲取目錄統計資訊"""
        try:
            abs_path = self.config.get_workspace_path(path)
            
            if not os.path.isdir(abs_path):
                raise NotADirectoryError(f"不是目錄: {path}")
            
            total_files = 0
            total_dirs = 0
            total_size = 0
            
            for root, dirs, files in os.walk(abs_path):
                total_dirs += len(dirs)
                total_files += len(files)
                
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        pass
            
            return {
                "path": abs_path,
                "total_files": total_files,
                "total_dirs": total_dirs,
                "total_size": total_size,
                "total_size_human": self._format_size(total_size)
            }
            
        except Exception as e:
            logger.error(f"獲取目錄統計失敗: {e}")
            return {"error": str(e)}
    
    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def clear_cache(self):
        """清除快取"""
        self.cache.clear()
        logger.info("檔案瀏覽器快取已清除")