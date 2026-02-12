#!/usr/bin/env python3
"""
OpenClaw 議題系統處理器（優化版）
這個腳本會被 OpenClaw 直接呼叫，使用優化版系統
"""

import json
import sys
import os

# 添加工作空間路徑
sys.path.append('/root/.openclaw/workspace')

def main():
    """主處理函數（優化版）"""
    if len(sys.argv) < 2:
        print("❌ 請提供輸入參數")
        print("使用方法: python3 handle_issue_system_optimized.py <輸入JSON>")
        sys.exit(1)
    
    try:
        # 解析輸入
        input_data = json.loads(sys.argv[1])
        user_input = input_data.get("text", "").strip()
        is_command = input_data.get("is_command", False)
        callback_data = input_data.get("callback_data")
        
        # 載入優化版議題系統
        from issue_integration_optimized import process_message_optimized, handle_callback_query_optimized
        
        if callback_data:
            # 處理 callback query
            result = handle_callback_query_optimized(callback_data)
        else:
            # 處理一般訊息或指令
            result = process_message_optimized(user_input, is_command)
        
        # 輸出結果
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            "text": f"❌ {str(e)[:30]}",
            "buttons": [],
            "metadata": {"error": str(e)}
        }
        print(json.dumps(error_result, ensure_ascii=False))

if __name__ == "__main__":
    main()