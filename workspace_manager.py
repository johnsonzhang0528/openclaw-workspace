#!/usr/bin/env python3
"""
工作空間管理工具 - 管理檔案、目錄和專案
"""

import json
import os
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import mimetypes

class WorkspaceManager:
    def __init__(self):
        self.base_dir = Path.home() / ".openclaw"
        self.workspace_dir = self.base_dir / "workspace"
        self.manager_dir = self.workspace_dir / "manager"
        
        # 配置文件
        self.bookmarks_file = self.manager_dir / "bookmarks.json"
        self.history_file = self.manager_dir / "history.json"
        
        # 當前路徑
        self.current_path = self.workspace_dir
        
        # 加載數據
        self.bookmarks = self._load_json(self.bookmarks_file, {"bookmarks": []})
        self.history = self._load_json(self.history_file, {
            "file_operations": [],
            "navigation_history": [],
            "search_history": [],
            "max_entries": 100
        })
    
    def _load_json(self, filepath, default=None):
        """加載 JSON 文件"""
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"加載 {filepath} 時出錯: {e}")
        return default if default is not None else {}
    
    def _save_json(self, filepath, data):
        """保存 JSON 文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"保存 {filepath} 時出錯: {e}")
            return False
    
    def _add_to_history(self, history_type, entry):
        """添加到歷史記錄"""
        if history_type in self.history:
            self.history[history_type].insert(0, {
                **entry,
                "timestamp": datetime.now().isoformat()
            })
            
            # 限制歷史記錄大小
            max_entries = self.history.get("max_entries", 100)
            if len(self.history[history_type]) > max_entries:
                self.history[history_type] = self.history[history_type][:max_entries]
            
            self._save_json(self.history_file, self.history)
    
    def list_directory(self, path=None, show_hidden=False):
        """列出目錄內容"""
        if path is None:
            path = self.current_path
        else:
            path = Path(path)
            if not path.is_absolute():
                path = self.current_path / path
        
        try:
            if not path.exists():
                return {"error": f"路徑不存在: {path}"}
            
            if not path.is_dir():
                return {"error": f"不是目錄: {path}"}
            
            items = []
            for item in path.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
                
                if item.is_file():
                    # 獲取文件類型
                    mime_type, _ = mimetypes.guess_type(str(item))
                    item_info["mime_type"] = mime_type or "unknown"
                    
                    # 獲取文件擴展名
                    item_info["extension"] = item.suffix.lower()
                
                items.append(item_info)
            
            # 排序：目錄在前，文件在後，按名稱排序
            items.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
            
            # 添加到導航歷史
            self._add_to_history("navigation_history", {
                "path": str(path),
                "action": "list"
            })
            
            return {
                "path": str(path),
                "items": items,
                "total": len(items),
                "parent": str(path.parent) if path != Path("/") else None
            }
        
        except PermissionError:
            return {"error": f"權限不足: {path}"}
        except Exception as e:
            return {"error": f"列出目錄時出錯: {e}"}
    
    def change_directory(self, path):
        """切換目錄"""
        try:
            new_path = Path(path)
            if not new_path.is_absolute():
                new_path = self.current_path / new_path
            
            # 解析路徑（處理 .. 和 .）
            new_path = new_path.resolve()
            
            if not new_path.exists():
                return {"error": f"路徑不存在: {new_path}"}
            
            if not new_path.is_dir():
                return {"error": f"不是目錄: {new_path}"}
            
            old_path = self.current_path
            self.current_path = new_path
            
            # 添加到歷史記錄
            self._add_to_history("navigation_history", {
                "from": str(old_path),
                "to": str(new_path),
                "action": "cd"
            })
            
            return {
                "success": True,
                "old_path": str(old_path),
                "new_path": str(new_path)
            }
        
        except PermissionError:
            return {"error": f"權限不足: {path}"}
        except Exception as e:
            return {"error": f"切換目錄時出錯: {e}"}
    
    def read_file(self, filepath, limit_lines=None):
        """讀取文件內容"""
        try:
            path = Path(filepath)
            if not path.is_absolute():
                path = self.current_path / path
            
            if not path.exists():
                return {"error": f"文件不存在: {path}"}
            
            if not path.is_file():
                return {"error": f"不是文件: {path}"}
            
            # 檢查文件大小（限制大文件）
            file_size = path.stat().st_size
            if file_size > 10 * 1024 * 1024:  # 10MB
                return {"error": f"文件太大 ({file_size} bytes)，請使用其他方式查看"}
            
            # 讀取文件
            encoding = self._detect_encoding(path)
            with open(path, 'r', encoding=encoding, errors='replace') as f:
                if limit_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= limit_lines:
                            lines.append("... (文件過長，已截斷)")
                            break
                        lines.append(line.rstrip('\n'))
                    content = '\n'.join(lines)
                else:
                    content = f.read()
            
            # 添加到歷史記錄
            self._add_to_history("file_operations", {
                "path": str(path),
                "action": "read",
                "size": file_size
            })
            
            return {
                "success": True,
                "path": str(path),
                "content": content,
                "size": file_size,
                "encoding": encoding,
                "lines": content.count('\n') + 1
            }
        
        except PermissionError:
            return {"error": f"權限不足: {filepath}"}
        except UnicodeDecodeError:
            return {"error": "無法解碼文件（可能是二進制文件）"}
        except Exception as e:
            return {"error": f"讀取文件時出錯: {e}"}
    
    def _detect_encoding(self, filepath):
        """檢測文件編碼"""
        try:
            # 簡單的編碼檢測
            import chardet
            with open(filepath, 'rb') as f:
                raw_data = f.read(1024)
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8')
        except:
            return 'utf-8'
    
    def create_file(self, filename, content=""):
        """創建文件"""
        try:
            path = Path(filename)
            if not path.is_absolute():
                path = self.current_path / path
            
            if path.exists():
                return {"error": f"文件已存在: {path}"}
            
            # 確保父目錄存在
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 寫入文件
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 添加到歷史記錄
            self._add_to_history("file_operations", {
                "path": str(path),
                "action": "create",
                "size": len(content)
            })
            
            return {
                "success": True,
                "path": str(path),
                "size": len(content)
            }
        
        except PermissionError:
            return {"error": f"權限不足: {filename}"}
        except Exception as e:
            return {"error": f"創建文件時出錯: {e}"}
    
    def create_directory(self, dirname):
        """創建目錄"""
        try:
            path = Path(dirname)
            if not path.is_absolute():
                path = self.current_path / path
            
            if path.exists():
                return {"error": f"目錄已存在: {path}"}
            
            path.mkdir(parents=True, exist_ok=True)
            
            # 添加到歷史記錄
            self._add_to_history("file_operations", {
                "path": str(path),
                "action": "mkdir"
            })
            
            return {
                "success": True,
                "path": str(path)
            }
        
        except PermissionError:
            return {"error": f"權限不足: {dirname}"}
        except Exception as e:
            return {"error": f"創建目錄時出錯: {e}"}
    
    def delete_path(self, target, recursive=False):
        """刪除文件或目錄"""
        try:
            path = Path(target)
            if not path.is_absolute():
                path = self.current_path / path
            
            if not path.exists():
                return {"error": f"路徑不存在: {path}"}
            
            # 記錄刪除信息
            if path.is_file():
                size = path.stat().st_size
                path.unlink()
            else:
                if recursive:
                    size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                    shutil.rmtree(path)
                else:
                    # 檢查目錄是否為空
                    if any(path.iterdir()):
                        return {"error": f"目錄非空，請使用遞歸刪除: {path}"}
                    size = 0
                    path.rmdir()
            
            # 添加到歷史記錄
            self._add_to_history("file_operations", {
                "path": str(path),
                "action": "delete",
                "recursive": recursive,
                "size": size
            })
            
            return {
                "success": True,
                "path": str(path),
                "type": "file" if path.is_file() else "directory",
                "size": size
            }
        
        except PermissionError:
            return {"error": f"權限不足: {target}"}
        except Exception as e:
            return {"error": f"刪除時出錯: {e}"}
    
    def search_files(self, query, path=None, file_types=None):
        """搜索文件"""
        try:
            if path is None:
                path = self.current_path
            else:
                path = Path(path)
                if not path.is_absolute():
                    path = self.current_path / path
            
            if not path.exists() or not path.is_dir():
                return {"error": f"無效的路徑: {path}"}
            
            results = []
            query_lower = query.lower()
            
            for item in path.rglob('*'):
                # 跳過隱藏文件
                if any(part.startswith('.') for part in item.parts):
                    continue
                
                # 文件類型過濾
                if file_types:
                    if item.is_file():
                        ext = item.suffix.lower()
                        if ext not in file_types:
                            continue
                    elif "directory" not in file_types:
                        continue
                
                # 搜索匹配
                if query_lower in item.name.lower():
                    item_info = {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0,
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    }
                    results.append(item_info)
            
            # 添加到搜索歷史
            self._add_to_history("search_history", {
                "query": query,
                "path": str(path),
                "results": len(results)
            })
            
            return {
                "success": True,
                "query": query,
                "path": str(path),
                "results": results,
                "count": len(results)
            }
        
        except PermissionError:
            return {"error": f"權限不足: {path}"}
        except Exception as e:
            return {"error": f"搜索時出錯: {e}"}
    
    def git_status(self, path=None):
        """獲取 Git 狀態"""
        try:
            if path is None:
                path = self.current_path
            else:
                path = Path(path)
                if not path.is_absolute():
                    path = self.current_path / path
            
            # 檢查是否為 Git 倉庫
            git_dir = path / ".git"
            if not git_dir.exists():
                return {"error": "不是 Git 倉庫"}
            
            # 執行 Git 命令
            commands = {
                "status": ["git", "status", "--short"],
                "branch": ["git", "branch", "--show-current"],
                "remote": ["git", "remote", "-v"],
                "log": ["git", "log", "--oneline", "-5"]
            }
            
            results = {}
            for name, cmd in commands.items():
                try:
                    result = subprocess.run(
                        cmd,
                        cwd=path,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        results[name] = result.stdout.strip()
                    else:
                        results[name] = f"錯誤: {result.stderr.strip()}"
                except subprocess.TimeoutExpired:
                    results[name] = "超時"
                except Exception as e:
                    results[name] = f"異常: {e}"
            
            return {
                "success": True,
                "path": str(path),
                "git_info": results
            }
        
        except Exception as e:
            return {"error": f"獲取 Git 狀態時出錯: {e}"}
    
    def add_bookmark(self, name, path):
        """添加書籤"""
        try:
            target_path = Path(path)
            if not target_path.is_absolute():
                target_path = self.current_path / target_path
            
            if not target_path.exists():
                return {"error": f"路徑不存在: {target_path}"}
            
            # 檢查是否已存在
            for bookmark in self.bookmarks.get("bookmarks", []):
                if bookmark.get("path") == str(target_path):
                    return {"error": "書籤已存在"}
            
            # 添加書籤
            new_bookmark = {
                "name": name,
                "path": str(target_path),
                "type": "directory" if target_path.is_dir() else "file",
                "created": datetime.now().isoformat()
            }
            
            self.bookmarks.setdefault("bookmarks", []).append(new_bookmark)
            
            if self._save_json(self.bookmarks_file, self.bookmarks):
                return {
                    "success": True,
                    "bookmark": new_bookmark
                }
            else:
                return {"error": "保存書籤失敗"}
        
        except Exception as e:
            return {"error": f"添加書籤時出錯: {e}"}
    
    def get_bookmarks(self):
        """獲取書籤列表"""
        return self.bookmarks.get("bookmarks", [])

def main():
    """主函數"""
    manager = WorkspaceManager()
    
    # 示例：列出當前目錄
    print(f"當前目錄: {manager.current_path}")
    result = manager.list_directory()
    
    if "error" in result:
        print(f"錯誤: {result['error']}")
    else:
        print(f"\n目錄內容 ({result['path']}):")
        for item in result["items"]:
            icon = "📂" if item["type"] == "directory" else "📄"
            print(f"{icon} {item['name']}")
    
    # 示例：創建測試文件
    print("\n創建測試文件...")
    result = manager.create_file("test.txt", "這是一個測試文件\n創建時間: " + datetime.now().isoformat())
    if "error" in result:
        print(f"錯誤: {result['error']}")
    else:
        print(f"成功創建: {result['path']}")
    
    # 示例：讀取文件
    print("\n讀取測試文件...")
    result = manager.read_file("test.txt")
    if "error" in result:
        print(f"錯誤: {result['error']}")
    else:
        print(f"文件內容:\n{result['content']}")
    
    # 示例：添加書籤
    print("\n添加書籤...")
    result = manager.add_bookmark("工作空間", str(manager.workspace_dir))
    if "error" in result:
        print(f"錯誤: {result['error']}")
    else:
        print(f"成功添加書籤: {result['bookmark']['name']}")

if __name__ == "__main__":
    main()