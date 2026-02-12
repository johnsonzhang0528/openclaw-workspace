#!/usr/bin/env python3
"""
智慧快捷指令系統 - 主入口點
提供快捷指令管理、模板引擎和自動化工作流程功能
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional, Callable
import signal
import sys

from .shortcut_manager import ShortcutManager
from .template_engine import TemplateEngine
from .config import Config
from .utils import setup_logging, validate_shortcut, format_shortcut_info

logger = logging.getLogger(__name__)

class SmartShortcuts:
    """智慧快捷指令系統主類別"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化快捷指令系統"""
        self.config = Config(config_path)
        self.shortcut_manager = ShortcutManager(self.config)
        self.template_engine = TemplateEngine(self.config)
        self.running = False
        self.handlers = {}
        
    async def start(self):
        """啟動快捷指令系統"""
        if self.running:
            logger.warning("快捷指令系統已在運行中")
            return
            
        logger.info("啟動智慧快捷指令系統...")
        
        # 設置信號處理
        self.setup_signal_handlers()
        
        try:
            # 載入快捷指令
            await self.shortcut_manager.load_shortcuts()
            
            # 載入模板
            await self.template_engine.load_templates()
            
            # 註冊預設處理器
            self._register_default_handlers()
            
            self.running = True
            logger.info(f"智慧快捷指令系統啟動完成，載入 {len(self.shortcut_manager.shortcuts)} 個快捷指令")
            
            # 主循環
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"快捷指令系統運行時發生錯誤: {e}")
            await self.stop()
            
    async def stop(self):
        """停止快捷指令系統"""
        if not self.running:
            return
            
        logger.info("停止智慧快捷指令系統...")
        self.running = False
        
        # 保存快捷指令
        await self.shortcut_manager.save_shortcuts()
        
        # 保存模板
        await self.template_engine.save_templates()
        
        logger.info("智慧快捷指令系統已停止")
        
    def setup_signal_handlers(self):
        """設置信號處理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信號 {signum}, 正在停止...")
            asyncio.create_task(self.stop())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def _register_default_handlers(self):
        """註冊預設處理器"""
        # 系統資訊處理器
        self.register_handler("system_info", self._handle_system_info)
        
        # 檔案操作處理器
        self.register_handler("file_operation", self._handle_file_operation)
        
        # 命令執行處理器
        self.register_handler("command_exec", self._handle_command_exec)
        
        # 模板渲染處理器
        self.register_handler("template_render", self._handle_template_render)
        
    def register_handler(self, handler_type: str, handler_func: Callable):
        """註冊處理器函數"""
        self.handlers[handler_type] = handler_func
        logger.debug(f"註冊處理器: {handler_type}")
        
    async def execute_shortcut(self, shortcut_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """執行快捷指令"""
        if not self.running:
            return {"success": False, "error": "系統未運行"}
            
        try:
            # 查找快捷指令
            shortcut = self.shortcut_manager.get_shortcut(shortcut_name)
            if not shortcut:
                return {"success": False, "error": f"找不到快捷指令: {shortcut_name}"}
                
            logger.info(f"執行快捷指令: {shortcut_name}")
            
            # 更新使用統計
            self.shortcut_manager.record_usage(shortcut_name)
            
            # 執行快捷指令
            result = await self._execute_shortcut_action(shortcut, context or {})
            
            return {
                "success": True,
                "shortcut": shortcut_name,
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"執行快捷指令時發生錯誤: {e}")
            return {"success": False, "error": str(e), "shortcut": shortcut_name}
            
    async def _execute_shortcut_action(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """執行快捷指令動作"""
        action_type = shortcut.get("action_type", "command")
        
        # 合併上下文
        merged_context = {**shortcut.get("context", {}), **context}
        
        # 根據動作類型執行
        if action_type == "command":
            return await self._handle_command_action(shortcut, merged_context)
        elif action_type == "template":
            return await self._handle_template_action(shortcut, merged_context)
        elif action_type == "custom":
            return await self._handle_custom_action(shortcut, merged_context)
        elif action_type == "workflow":
            return await self._handle_workflow_action(shortcut, merged_context)
        else:
            raise ValueError(f"不支援的動作類型: {action_type}")
            
    async def _handle_command_action(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理命令動作"""
        command = shortcut.get("command", "")
        if not command:
            return {"success": False, "error": "命令為空"}
            
        # 渲染命令模板
        rendered_command = self.template_engine.render_template(command, context)
        
        # 執行命令
        try:
            process = await asyncio.create_subprocess_shell(
                rendered_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "command": rendered_command,
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore')
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "command": rendered_command}
            
    async def _handle_template_action(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理模板動作"""
        template_name = shortcut.get("template", "")
        if not template_name:
            return {"success": False, "error": "模板名稱為空"}
            
        # 渲染模板
        result = await self.template_engine.render_template_by_name(template_name, context)
        
        return {
            "success": True,
            "template": template_name,
            "result": result
        }
        
    async def _handle_custom_action(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理自定義動作"""
        handler_type = shortcut.get("handler", "")
        if not handler_type:
            return {"success": False, "error": "處理器類型為空"}
            
        # 查找處理器
        handler = self.handlers.get(handler_type)
        if not handler:
            return {"success": False, "error": f"找不到處理器: {handler_type}"}
            
        # 執行處理器
        try:
            result = await handler(shortcut, context)
            return {"success": True, "handler": handler_type, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e), "handler": handler_type}
            
    async def _handle_workflow_action(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理工作流程動作"""
        workflow = shortcut.get("workflow", [])
        if not workflow:
            return {"success": False, "error": "工作流程為空"}
            
        results = []
        current_context = context.copy()
        
        for step in workflow:
            step_type = step.get("type", "shortcut")
            step_name = step.get("name", "")
            
            if step_type == "shortcut":
                # 執行子快捷指令
                result = await self.execute_shortcut(step_name, current_context)
                results.append(result)
                
                if not result.get("success", False):
                    return {
                        "success": False,
                        "error": f"工作流程步驟失敗: {step_name}",
                        "results": results
                    }
                    
                # 更新上下文
                if "result" in result:
                    current_context[f"step_{step_name}"] = result["result"]
                    
            elif step_type == "condition":
                # 條件判斷
                condition = step.get("condition", "")
                if condition:
                    # 簡單的條件判斷（可擴展為完整的表達式引擎）
                    pass
                    
            elif step_type == "loop":
                # 循環執行
                loop_items = step.get("items", [])
                loop_var = step.get("var", "item")
                
                for item in loop_items:
                    current_context[loop_var] = item
                    # 執行循環體
                    pass
                    
        return {
            "success": True,
            "workflow": shortcut.get("name", ""),
            "results": results
        }
        
    async def _handle_system_info(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理系統資訊請求"""
        import platform
        import psutil
        import time
        
        return {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "boot_time": psutil.boot_time(),
            "timestamp": time.time()
        }
        
    async def _handle_file_operation(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理檔案操作"""
        operation = shortcut.get("operation", "read")
        filepath = shortcut.get("filepath", "")
        
        if not filepath:
            return {"success": False, "error": "檔案路徑為空"}
            
        try:
            if operation == "read":
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"success": True, "operation": "read", "content": content}
                
            elif operation == "write":
                content = shortcut.get("content", "")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return {"success": True, "operation": "write"}
                
            elif operation == "append":
                content = shortcut.get("content", "")
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(content)
                return {"success": True, "operation": "append"}
                
            elif operation == "delete":
                os.remove(filepath)
                return {"success": True, "operation": "delete"}
                
            else:
                return {"success": False, "error": f"不支援的檔案操作: {operation}"}
                
        except Exception as e:
            return {"success": False, "error": str(e), "operation": operation}
            
    async def _handle_command_exec(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理命令執行"""
        return await self._handle_command_action(shortcut, context)
        
    async def _handle_template_render(self, shortcut: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """處理模板渲染"""
        return await self._handle_template_action(shortcut, context)
        
    def get_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        return {
            "running": self.running,
            "shortcuts_count": len(self.shortcut_manager.shortcuts),
            "templates_count": len(self.template_engine.templates),
            "handlers_count": len(self.handlers),
            "config": self.config.get_summary()
        }
        
    async def list_shortcuts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出快捷指令"""
        return self.shortcut_manager.list_shortcuts(category)
        
    async def create_shortcut(self, shortcut_data: Dict[str, Any]) -> Dict[str, Any]:
        """創建快捷指令"""
        return await self.shortcut_manager.create_shortcut(shortcut_data)
        
    async def update_shortcut(self, name: str, shortcut_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新快捷指令"""
        return await self.shortcut_manager.update_shortcut(name, shortcut_data)
        
    async def delete_shortcut(self, name: str) -> Dict[str, Any]:
        """刪除快捷指令"""
        return await self.shortcut_manager.delete_shortcut(name)
        
    async def get_shortcut_stats(self) -> Dict[str, Any]:
        """獲取快捷指令統計"""
        return self.shortcut_manager.get_stats()

async def main():
    """主函數"""
    # 設置日誌
    setup_logging()
    
    # 創建快捷指令系統實例
    shortcuts_system = SmartShortcuts()
    
    try:
        # 啟動系統
        await shortcuts_system.start()
        
    except KeyboardInterrupt:
        logger.info("收到中斷信號")
    except Exception as e:
        logger.error(f"主程序錯誤: {e}")
    finally:
        # 確保清理
        await shortcuts_system.stop()

if __name__ == "__main__":
    # 運行主程序
    asyncio.run(main())