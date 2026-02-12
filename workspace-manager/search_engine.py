#!/usr/bin/env python3
"""
搜尋引擎模組 - 提供檔案名稱和內容搜尋功能
"""

import os
import re
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """搜尋類型枚舉"""
    FILENAME = "filename"
    CONTENT = "content"
    BOTH = "both"


@dataclass
class SearchResult:
    """搜尋結果類別"""
    path: str
    filename: str
    type: str  # file, directory
    score: float = 0.0
    matches: List[Dict[str, Any]] = field(default_factory=list)
    preview: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "path": self.path,
            "filename": self.filename,
            "type": self.type,
            "score": self.score,
            "match_count": len(self.matches),
            "preview": self.preview[:200] + "..." if len(self.preview) > 200 else self.preview
        }


class SearchEngine:
    """搜尋引擎類別"""
    
    def __init__(self, config):
        """初始化搜尋引擎"""
        self.config = config
        self.search_history = []
        self._load_search_history()
    
    def search(self, query: str, search_path: str = "", 
               search_type: SearchType = SearchType.BOTH,
               case_sensitive: bool = False,
               use_regex: bool = False,
               max_results: int = 50) -> List[SearchResult]:
        """執行搜尋"""
        try:
            start_time = time.time()
            
            # 記錄搜尋歷史
            self._add_to_history(query, search_type.value)
            
            # 獲取搜尋路徑
            if not search_path:
                search_path = self.config.workspace_root
            abs_path = self.config.get_workspace_path(search_path)
            
            if not os.path.isdir(abs_path):
                raise NotADirectoryError(f"搜尋路徑不是目錄: {search_path}")
            
            # 準備搜尋模式
            if use_regex:
                try:
                    pattern = re.compile(query if case_sensitive else query, re.IGNORECASE)
                except re.error as e:
                    raise ValueError(f"無效的正則表達式: {e}")
            else:
                # 轉義特殊字符
                escaped_query = re.escape(query)
                pattern = re.compile(escaped_query if case_sensitive else escaped_query, re.IGNORECASE)
            
            # 執行搜尋
            results = []
            
            for root, dirs, files in os.walk(abs_path):
                # 搜尋目錄名稱
                if search_type in [SearchType.FILENAME, SearchType.BOTH]:
                    for dir_name in dirs:
                        if self._match_pattern(dir_name, pattern, case_sensitive, use_regex):
                            result = SearchResult(
                                path=os.path.join(root, dir_name),
                                filename=dir_name,
                                type="directory",
                                score=1.0
                            )
                            results.append(result)
                
                # 搜尋檔案名稱
                if search_type in [SearchType.FILENAME, SearchType.BOTH]:
                    for file_name in files:
                        if self._match_pattern(file_name, pattern, case_sensitive, use_regex):
                            result = SearchResult(
                                path=os.path.join(root, file_name),
                                filename=file_name,
                                type="file",
                                score=1.0
                            )
                            results.append(result)
                
                # 搜尋檔案內容
                if search_type in [SearchType.CONTENT, SearchType.BOTH]:
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        
                        # 檢查檔案是否可搜尋
                        if not self._is_searchable_file(file_path):
                            continue
                        
                        content_matches = self._search_in_file(file_path, pattern, case_sensitive, use_regex)
                        if content_matches:
                            # 創建預覽
                            preview = self._create_preview(file_path, content_matches)
                            
                            result = SearchResult(
                                path=file_path,
                                filename=file_name,
                                type="file",
                                score=len(content_matches) / 10.0,  # 基於匹配數量評分
                                matches=content_matches,
                                preview=preview
                            )
                            results.append(result)
            
            # 按分數排序
            results.sort(key=lambda x: x.score, reverse=True)
            
            # 限制結果數量
            results = results[:max_results]
            
            # 計算搜尋時間
            search_time = time.time() - start_time
            
            logger.info(f"搜尋完成: '{query}' 找到 {len(results)} 個結果，耗時 {search_time:.2f} 秒")
            
            return results
            
        except Exception as e:
            logger.error(f"搜尋失敗: {e}")
            raise
    
    def _match_pattern(self, text: str, pattern: re.Pattern, 
                      case_sensitive: bool, use_regex: bool) -> bool:
        """匹配模式"""
        if use_regex:
            return bool(pattern.search(text))
        else:
            if case_sensitive:
                return pattern.pattern in text
            else:
                return pattern.pattern.lower() in text.lower()
    
    def _is_searchable_file(self, filepath: str) -> bool:
        """檢查檔案是否可搜尋"""
        try:
            # 檢查檔案大小
            file_size = os.path.getsize(filepath)
            if file_size > self.config.max_file_size:
                return False
            
            # 檢查副檔名
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in self.config.allowed_extensions:
                return False
            
            # 檢查是否為文字檔案（簡單檢查）
            if file_size > 1024 * 1024:  # 1MB以上不搜尋內容
                return False
            
            return True
            
        except Exception:
            return False
    
    def _search_in_file(self, filepath: str, pattern: re.Pattern,
                       case_sensitive: bool, use_regex: bool) -> List[Dict[str, Any]]:
        """在檔案中搜尋內容"""
        matches = []
        
        try:
            # 嘗試讀取檔案
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 嘗試其他編碼
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception:
                return matches  # 無法讀取檔案
        
        # 搜尋匹配
        if use_regex:
            for match in pattern.finditer(content):
                matches.append({
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group()
                })
        else:
            search_text = pattern.pattern
            if not case_sensitive:
                content_lower = content.lower()
                search_text = search_text.lower()
                offset = 0
                while True:
                    pos = content_lower.find(search_text, offset)
                    if pos == -1:
                        break
                    matches.append({
                        "start": pos,
                        "end": pos + len(search_text),
                        "text": content[pos:pos + len(search_text)]
                    })
                    offset = pos + 1
            else:
                offset = 0
                while True:
                    pos = content.find(search_text, offset)
                    if pos == -1:
                        break
                    matches.append({
                        "start": pos,
                        "end": pos + len(search_text),
                        "text": content[pos:pos + len(search_text)]
                    })
                    offset = pos + 1
        
        return matches
    
    def _create_preview(self, filepath: str, matches: List[Dict[str, Any]]) -> str:
        """創建搜尋結果預覽"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
            except Exception:
                return "[無法讀取檔案]"
        
        # 找到包含匹配的行
        preview_lines = []
        line_starts = [0]
        for line in lines:
            line_starts.append(line_starts[-1] + len(line))
        
        for match in matches[:3]:  # 最多顯示3個匹配
            # 找到匹配所在的行
            line_idx = 0
            for i in range(len(line_starts) - 1):
                if line_starts[i] <= match["start"] < line_starts[i + 1]:
                    line_idx = i
                    break
            
            # 獲取上下文（前後各1行）
            start_line = max(0, line_idx - 1)
            end_line = min(len(lines), line_idx + 2)
            
            for i in range(start_line, end_line):
                line_text = lines[i].rstrip('\n')
                if i == line_idx:
                    # 高亮匹配部分
                    line_start = line_starts[i]
                    match_in_line_start = match["start"] - line_start
                    match_in_line_end = match["end"] - line_start
                    
                    if 0 <= match_in_line_start < len(line_text):
                        highlighted = (
                            line_text[:match_in_line_start] +
                            "**" + line_text[match_in_line_start:match_in_line_end] + "**" +
                            line_text[match_in_line_end:]
                        )
                        preview_lines.append(f"{i+1}: {highlighted}")
                    else:
                        preview_lines.append(f"{i+1}: {line_text}")
                else:
                    preview_lines.append(f"{i+1}: {line_text}")
            
            if len(preview_lines) >= 10:  # 最多10行預覽
                break
        
        return "\n".join(preview_lines[:10])
    
    def _add_to_history(self, query: str, search_type: str):
        """添加到搜尋歷史"""
        history_item = {
            "query": query,
            "type": search_type,
            "timestamp": time.time(),
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.search_history.insert(0, history_item)
        
        # 限制歷史記錄數量
        if len(self.search_history) > self.config.search_history_size:
            self.search_history = self.search_history[:self.config.search_history_size]
        
        # 保存歷史記錄
        self._save_search_history()
    
    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取搜尋歷史"""
        return self.search_history[:limit]
    
    def clear_search_history(self):
        """清除搜尋歷史"""
        self.search_history = []
        self._save_search_history()
        logger.info("搜尋歷史已清除")
    
    def _load_search_history(self):
        """加載搜尋歷史"""
        history_file = os.path.join(self.config.data_path, "search_history.json")
        
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.search_history = json.load(f)
                logger.info(f"已加載 {len(self.search_history)} 條搜尋歷史")
            except Exception as e:
                logger.error(f"加載搜尋歷史失敗: {e}")
                self.search_history = []
    
    def _save_search_history(self):
        """保存搜尋歷史"""
        history_file = os.path.join(self.config.data_path, "search_history.json")
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.search_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存搜尋歷史失敗: {e}")
    
    def get_file_types_stats(self, path: str = "") -> Dict[str, int]:
        """獲取檔案類型統計"""
        try:
            if not path:
                path = self.config.workspace_root
            abs_path = self.config.get_workspace_path(path)
            
            if not os.path.isdir(abs_path):
                raise NotADirectoryError(f"不是目錄: {path}")
            
            type_stats = {}
            
            for root, dirs, files in os.walk(abs_path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        type_stats[ext] = type_stats.get(ext, 0) + 1
                    else:
                        type_stats["[無副檔名]"] = type_stats.get("[無副檔名]", 0) + 1
            
            # 按數量排序
            sorted_stats = dict(sorted(type_stats.items(), key=lambda x: x[1], reverse=True))
            
            return sorted_stats
            
        except Exception as e:
            logger.error(f"獲取檔案類型統計失敗: {e}")
            return {}