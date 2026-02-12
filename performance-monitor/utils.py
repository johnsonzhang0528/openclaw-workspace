#!/usr/bin/env python3
"""
工具函數模組
"""

import os
import sys
import json
import time
import hashlib
import logging
import subprocess
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def get_current_timestamp() -> str:
    """獲取當前時間戳"""
    return datetime.now().isoformat()


def get_uptime() -> str:
    """獲取運行時間"""
    # 這裡可以實現獲取技能運行時間的邏輯
    # 目前返回固定值
    return "0 days, 0:00:00"


def format_size(size_bytes: int) -> str:
    """格式化檔案大小
    
    Args:
        size_bytes: 位元組大小
        
    Returns:
        格式化後的大小字串
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """格式化時間間隔
    
    Args:
        seconds: 秒數
        
    Returns:
        格式化後的時間字串
    """
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


def safe_json_load(filepath: str, default: Any = None) -> Any:
    """安全加載 JSON 檔案
    
    Args:
        filepath: 檔案路徑
        default: 預設值
        
    Returns:
        加載的數據或預設值
    """
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加載 JSON 檔案失敗 {filepath}: {e}")
    
    return default


def safe_json_save(data: Any, filepath: str, indent: int = 2) -> bool:
    """安全儲存 JSON 檔案
    
    Args:
        data: 要儲存的數據
        filepath: 檔案路徑
        indent: 縮進空格數
        
    Returns:
        是否成功
    """
    try:
        # 確保目錄存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        return True
    except Exception as e:
        logger.error(f"儲存 JSON 檔案失敗 {filepath}: {e}")
        return False


def calculate_file_hash(filepath: str, algorithm: str = 'sha256') -> Optional[str]:
    """計算檔案雜湊值
    
    Args:
        filepath: 檔案路徑
        algorithm: 雜湊算法
        
    Returns:
        雜湊值或 None
    """
    try:
        if not os.path.exists(filepath):
            return None
        
        hash_func = hashlib.new(algorithm)
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    except Exception as e:
        logger.error(f"計算檔案雜湊失敗 {filepath}: {e}")
        return None


def run_command(cmd: Union[str, List[str]], timeout: int = 30) -> Dict[str, Any]:
    """執行命令
    
    Args:
        cmd: 命令字串或列表
        timeout: 超時時間（秒）
        
    Returns:
        執行結果
    """
    try:
        if isinstance(cmd, str):
            cmd = cmd.split()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8'
        )
        
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'command': ' '.join(cmd)
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'timeout',
            'message': f'命令執行超時 ({timeout}秒)',
            'command': ' '.join(cmd) if isinstance(cmd, list) else cmd
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'執行命令失敗: {e}',
            'command': ' '.join(cmd) if isinstance(cmd, list) else cmd
        }


def validate_email(email: str) -> bool:
    """驗證電子郵件格式
    
    Args:
        email: 電子郵件地址
        
    Returns:
        是否有效
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """驗證 URL 格式
    
    Args:
        url: URL 地址
        
    Returns:
        是否有效
    """
    import re
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def sanitize_filename(filename: str) -> str:
    """清理檔案名稱
    
    Args:
        filename: 原始檔案名稱
        
    Returns:
        清理後的檔案名稱
    """
    import re
    
    # 移除非法字元
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # 移除開頭和結尾的點和空格
    filename = filename.strip('. ')
    
    # 限制長度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename


def create_backup(filepath: str, backup_dir: str = None) -> Optional[str]:
    """創建檔案備份
    
    Args:
        filepath: 原始檔案路徑
        backup_dir: 備份目錄
        
    Returns:
        備份檔案路徑或 None
    """
    try:
        if not os.path.exists(filepath):
            return None
        
        # 設置備份目錄
        if backup_dir is None:
            backup_dir = os.path.join(os.path.dirname(filepath), 'backups')
        
        os.makedirs(backup_dir, exist_ok=True)
        
        # 創建備份檔案名稱
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.basename(filepath)
        backup_name = f"{filename}.{timestamp}.bak"
        backup_path = os.path.join(backup_dir, backup_name)
        
        # 複製檔案
        import shutil
        shutil.copy2(filepath, backup_path)
        
        logger.info(f"已創建備份: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"創建備份失敗 {filepath}: {e}")
        return None


def get_system_info() -> Dict[str, Any]:
    """獲取系統信息
    
    Returns:
        系統信息字典
    """
    info = {
        'platform': sys.platform,
        'python_version': sys.version,
        'python_path': sys.executable,
        'cwd': os.getcwd(),
        'timestamp': get_current_timestamp()
    }
    
    try:
        import platform
        info.update({
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor()
        })
    except:
        pass
    
    try:
        import psutil
        info.update({
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('/')._asdict()
        })
    except:
        pass
    
    return info


def retry_on_failure(func, max_attempts: int = 3, delay: float = 1.0, 
                    exceptions: tuple = (Exception,)) -> Any:
    """重試裝飾器/函數
    
    Args:
        func: 要重試的函數
        max_attempts: 最大嘗試次數
        delay: 重試延遲（秒）
        exceptions: 要捕獲的異常類型
        
    Returns:
        函數結果
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    logger.warning(f"嘗試 {attempt + 1}/{max_attempts} 失敗: {e}")
                    time.sleep(delay * (2 ** attempt))  # 指數退避
                else:
                    logger.error(f"所有 {max_attempts} 次嘗試都失敗")
        
        raise last_exception
    
    return wrapper


class Timer:
    """計時器類別"""
    
    def __init__(self, name: str = None):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.time()
    
    @property
    def elapsed(self) -> float:
        """獲取經過的時間"""
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time
    
    def get_formatted_elapsed(self) -> str:
        """獲取格式化後的經過時間"""
        return format_duration(self.elapsed)
    
    def print_elapsed(self):
        """打印經過的時間"""
        if self.name:
            print(f"{self.name}: {self.get_formatted_elapsed()}")
        else:
            print(f"經過時間: {self.get_formatted_elapsed()}")


def measure_performance(func):
    """效能測量裝飾器"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with Timer(func.__name__) as timer:
            result = func(*args, **kwargs)
        
        logger.info(f"{func.__name__} 執行時間: {timer.get_formatted_elapsed()}")
        return result
    
    return wrapper


if __name__ == '__main__':
    # 測試工具函數
    print(f"當前時間戳: {get_current_timestamp()}")
    print(f"格式化大小: {format_size(123456789)}")
    print(f"格式化時間: {format_duration(3661.5)}")
    
    # 測試命令執行
    result = run_command(['echo', 'Hello, World!'])
    print(f"命令執行結果: {result}")
    
    # 測試系統信息
    info = get_system_info()
    print(f"系統信息: {json.dumps(info, indent=2, ensure_ascii=False)}")
    
    # 測試計時器
    with Timer('測試計時器') as timer:
        time.sleep(0.5)
    print(f"計時器結果: {timer.get_formatted_elapsed()}")