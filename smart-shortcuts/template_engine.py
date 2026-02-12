#!/usr/bin/env python3
"""
模板引擎
提供模板渲染、變數替換和條件邏輯功能
"""

import asyncio
import logging
import json
import os
import re
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import jinja2
from jinja2 import Template, Environment, FileSystemLoader

from .config import Config
from .utils import setup_logging, validate_template, format_template_info

logger = logging.getLogger(__name__)

class TemplateEngine:
    """模板引擎"""
    
    def __init__(self, config: Config):
        """初始化模板引擎"""
        self.config = config
        self.templates = {}
        self.environment = None
        self.filters = {}
        self.functions = {}
        self.loaded = False
        
        # 初始化 Jinja2 環境
        self._init_jinja2_environment()
        
    def _init_jinja2_environment(self):
        """初始化 Jinja2 環境"""
        # 創建環境
        self.environment = Environment(
            loader=FileSystemLoader(self.config.templates_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 註冊自定義過濾器
        self._register_default_filters()
        
        # 註冊自定義函數
        self._register_default_functions()
        
    def _register_default_filters(self):
        """註冊預設過濾器"""
        # JSON 格式化
        self.environment.filters['tojson'] = lambda obj: json.dumps(obj, ensure_ascii=False)
        
        # 日期格式化
        self.environment.filters['dateformat'] = lambda dt, fmt: dt.strftime(fmt) if isinstance(dt, datetime) else dt
        
        # 字串處理
        self.environment.filters['truncate'] = lambda s, length: (s[:length] + '...') if len(s) > length else s
        self.environment.filters['upper'] = lambda s: s.upper() if s else ''
        self.environment.filters['lower'] = lambda s: s.lower() if s else ''
        
        # 數字格式化
        self.environment.filters['format_bytes'] = self._format_bytes_filter
        self.environment.filters['format_percentage'] = self._format_percentage_filter
        
    def _register_default_functions(self):
        """註冊預設函數"""
        # 現在時間
        self.environment.globals['now'] = datetime.now
        
        # 環境變數
        self.environment.globals['env'] = os.environ.get
        
        # 工具函數
        self.environment.globals['len'] = len
        self.environment.globals['range'] = range
        self.environment.globals['list'] = list
        self.environment.globals['dict'] = dict
        
    def _format_bytes_filter(self, bytes_value: int) -> str:
        """格式化位元組數"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
        
    def _format_percentage_filter(self, value: float) -> str:
        """格式化百分比"""
        return f"{value:.1f}%"
        
    async def load_templates(self):
        """載入模板"""
        templates_dir = self.config.templates_dir
        
        try:
            # 確保模板目錄存在
            os.makedirs(templates_dir, exist_ok=True)
            
            # 載入模板檔案
            for filename in os.listdir(templates_dir):
                if filename.endswith('.j2') or filename.endswith('.jinja2'):
                    template_name = os.path.splitext(filename)[0]
                    template_path = os.path.join(templates_dir, filename)
                    
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                        
                    self.templates[template_name] = {
                        "name": template_name,
                        "filename": filename,
                        "content": template_content,
                        "path": template_path,
                        "created_at": datetime.fromtimestamp(os.path.getctime(template_path)).isoformat(),
                        "updated_at": datetime.fromtimestamp(os.path.getmtime(template_path)).isoformat()
                    }
                    
            # 創建預設模板
            if not self.templates:
                self._create_default_templates()
                
            logger.info(f"載入 {len(self.templates)} 個模板")
            self.loaded = True
            
        except Exception as e:
            logger.error(f"載入模板時發生錯誤: {e}")
            self._create_default_templates()
            
    async def save_templates(self):
        """保存模板"""
        try:
            # 確保模板目錄存在
            os.makedirs(self.config.templates_dir, exist_ok=True)
            
            # 保存每個模板
            for template_name, template_data in self.templates.items():
                template_path = os.path.join(self.config.templates_dir, f"{template_name}.j2")
                
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(template_data["content"])
                    
            logger.debug("模板已保存")
            
        except Exception as e:
            logger.error(f"保存模板時發生錯誤: {e}")
            
    def _create_default_templates(self):
        """創建預設模板"""
        default_templates = {
            "system_info": {
                "name": "系統資訊",
                "content": """系統資訊報告
================

時間: {{ now().strftime('%Y-%m-%d %H:%M:%S') }}

系統資訊:
- 主機名稱: {{ system_info.node }}
- 系統: {{ system_info.system }} {{ system_info.release }}
- 架構: {{ system_info.machine }}
- 處理器: {{ system_info.processor }}

資源使用情況:
- CPU 核心數: {{ system_info.cpu_count }}
- CPU 使用率: {{ system_info.cpu_percent }}%
- 記憶體使用率: {{ system_info.memory_percent }}%
- 磁碟使用率: {{ system_info.disk_percent }}%

系統運行時間: {{ (now().timestamp() - system_info.boot_time) | int }} 秒
""",
                "description": "系統資訊報告模板",
                "category": "report",
                "tags": ["system", "info", "report"]
            },
            "command_output": {
                "name": "命令輸出",
                "content": """命令執行結果
================

命令: {{ command }}
執行時間: {{ timestamp | dateformat('%Y-%m-%d %H:%M:%S') }}

返回碼: {{ returncode }}

標準輸出:
```
{{ stdout }}
```

{% if stderr %}
標準錯誤:
```
{{ stderr }}
```
{% endif %}

{% if success %}
狀態: ✅ 成功
{% else %}
狀態: ❌ 失敗
{% endif %}
""",
                "description": "命令輸出格式化模板",
                "category": "output",
                "tags": ["command", "output", "format"]
            },
            "file_list": {
                "name": "檔案列表",
                "content": """檔案列表
==========

路徑: {{ path }}
時間: {{ now().strftime('%Y-%m-%d %H:%M:%S') }}

檔案列表:
{% for file in files %}
- {{ file.name }} ({{ file.size | format_bytes }}) - {{ file.modified | dateformat('%Y-%m-%d %H:%M') }}
{% endfor %}

總計: {{ files | length }} 個檔案
""",
                "description": "檔案列表模板",
                "category": "file",
                "tags": ["file", "list", "directory"]
            },
            "error_report": {
                "name": "錯誤報告",
                "content": """錯誤報告
==========

時間: {{ now().strftime('%Y-%m-%d %H:%M:%S') }}
錯誤類型: {{ error_type }}

錯誤訊息:
```
{{ error_message }}
```

{% if traceback %}
堆疊追蹤:
```
{{ traceback }}
```
{% endif %}

{% if context %}
上下文資訊:
{{ context | tojson(indent=2) }}
{% endif %}
""",
                "description": "錯誤報告模板",
                "category": "error",
                "tags": ["error", "report", "debug"]
            }
        }
        
        self.templates = default_templates
        self.loaded = True
        logger.info(f"創建 {len(self.templates)} 個預設模板")
        
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """獲取模板"""
        return self.templates.get(name)
        
    def list_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出模板"""
        if category:
            return [t for t in self.templates.values() if t.get("category") == category]
        else:
            return list(self.templates.values())
            
    async def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """創建模板"""
        try:
            # 驗證數據
            validation_result = validate_template(template_data)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
                
            name = template_data.get("name")
            if not name:
                return {"success": False, "error": "模板名稱不能為空"}
                
            # 檢查是否已存在
            if name in self.templates:
                return {"success": False, "error": f"模板 '{name}' 已存在"}
                
            # 添加元數據
            template_data["created_at"] = datetime.now().isoformat()
            template_data["updated_at"] = datetime.now().isoformat()
            
            # 添加到引擎
            self.templates[name] = template_data
            
            # 保存到檔案
            await self.save_templates()
            
            logger.info(f"創建模板: {name}")
            
            return {
                "success": True,
                "template": name,
                "data": template_data
            }
            
        except Exception as e:
            logger.error(f"創建模板時發生錯誤: {e}")
            return {"success": False, "error": str(e)}
            
    async def update_template(self, name: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新模板"""
        try:
            # 檢查是否存在
            if name not in self.templates:
                return {"success": False, "error": f"模板 '{name}' 不存在"}
                
            # 獲取原始數據
            original_template = self.templates[name]
            
            # 更新數據
            updated_template = {**original_template, **template_data}
            updated_template["updated_at"] = datetime.now().isoformat()
            
            # 驗證數據
            validation_result = validate_template(updated_template)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
                
            # 更新引擎
            self.templates[name] = updated_template
            
            # 保存到檔案
            await self.save_templates()
            
            logger.info(f"更新模板: {name}")
            
            return {
                "success": True,
                "template": name,
                "data": updated_template
            }
            
        except Exception as e:
            logger.error(f"更新模板時發生錯誤: {e}")
            return {"success": False, "error": str(e)}
            
    async def delete_template(self, name: str) -> Dict[str, Any]:
        """刪除模板"""
        try:
            # 檢查是否存在
            if name not in self.templates:
                return {"success": False, "error": f"模板 '{name}' 不存在"}
                
            # 從引擎中移除
            del self.templates[name]
            
            # 刪除檔案
            template_path = os.path.join(self.config.templates_dir, f"{name}.j2")
            if os.path.exists(template_path):
                os.remove(template_path)
                
            logger.info(f"刪除模板: {name}")
            
            return {
                "success": True,
                "template": name,
                "message": f"模板 '{name}' 已刪除"
            }
            
        except Exception as e:
            logger.error(f"刪除模板時發生錯誤: {e}")
            return {"success": False, "error": str(e)}
            
    def render_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """渲染模板內容"""
        try:
            # 創建模板
            template = self.environment.from_string(template_content)
            
            # 渲染模板
            result = template.render(**context)
            
            return result
            
        except Exception as e:
            logger.error(f"渲染模板時發生錯誤: {e}")
            raise
            
    async def render_template_by_name(self, template_name: str, context: Dict[str, Any]) -> str:
        """根據名稱渲染模板"""
        try:
            # 獲取模板
            template_data = self.get_template(template_name)
            if not template_data:
                raise ValueError(f"模板 '{template_name}' 不存在")
                
            # 渲染模板
            result = self.render_template(template_data["content"], context)
            
            return result
            
        except Exception as e:
            logger.error(f"渲染模板 '{template_name}' 時發生錯誤: {e}")
            raise
            
    def register_filter(self, name: str, filter_func: Callable):
        """註冊自定義過濾器"""
        self.environment.filters[name] = filter_func
        self.filters[name] = filter_func
        logger.debug(f"註冊過濾器: {name}")
        
    def register_function(self, name: str, function_func: Callable):
        """註冊自定義函數"""
        self.environment.globals[name] = function_func
        self.functions[name] = function_func
        logger.debug(f"註冊函數: {name}")
        
    def validate_template_syntax(self, template_content: str) -> Dict[str, Any]:
        """驗證模板語法"""
        try:
            # 嘗試編譯模板
            self.environment.from_string(template_content)
            
            return {
                "valid": True,
                "message": "模板語法正確"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": f"模板語法錯誤: {e}"
            }
            
    def extract_variables(self, template_content: str) -> List[str]:
        """提取模板中的變數"""
        try:
            # 使用正則表達式提取變數
            variable_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
            variables = re.findall(variable_pattern, template_content)
            
            # 去重並排序
            unique_variables = sorted(set(variables))
            
            return unique_variables
            
        except Exception as e:
            logger.error(f"提取變數時發生錯誤: {e}")
            return []
            
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """獲取模板詳細資訊"""
        template_data = self.get_template(template_name)
        if not template_data:
            return {}
            
        # 提取變數
        variables = self.extract_variables(template_data["content"])
        
        # 驗證語法
        syntax_check = self.validate_template_syntax(template_data["content"])
        
        return {
            "name": template_data["name"],
            "description": template_data.get("description", ""),
            "category": template_data.get("category", "uncategorized"),
            "tags": template_data.get("tags", []),
            "variables": variables,
            "syntax_valid": syntax_check["valid"],
            "syntax_message": syntax_check.get("message", ""),
            "created_at": template_data.get("created_at"),
            "updated_at": template_data.get("updated_at"),
            "content_preview": template_data["content"][:200] + ("..." if len(template_data["content"]) > 200 else "")
        }
        
    async def batch_render(self, templates: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """批次渲染多個模板"""
        results = {}
        
        for template_info in templates:
            template_name = template_info.get("name")
            if not template_name:
                continue
                
            try:
                result = await self.render_template_by_name(template_name, context)
                results[template_name] = {
                    "success": True,
                    "result": result
                }
            except Exception as e:
                results[template_name] = {
                    "success": False,
                    "error": str(e)
                }
                
        return results
        
    def get_status(self) -> Dict[str, Any]:
        """獲取引擎狀態"""
        return {
            "loaded": self.loaded,
            "templates_count": len(self.templates),
            "filters_count": len(self.filters),
            "functions_count": len(self.functions),
            "config": self.config.get_summary()
        }