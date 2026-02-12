#!/usr/bin/env python3
"""
全域優化處理器 - OpenClaw 整合
這個腳本會被 OpenClaw 直接呼叫，優化所有回覆內容
"""

import json
import sys
import os

# 添加工作空間路徑
sys.path.append('/root/.openclaw/workspace')

def main():
    """主處理函數"""
    if len(sys.argv) < 2:
        print("❌ 請提供輸入參數")
        print("使用方法: python3 handle_global_optimization.py <輸入JSON>")
        sys.exit(1)
    
    try:
        # 解析輸入
        input_data = json.loads(sys.argv[1])
        
        # 提取必要資訊
        user_input = input_data.get("text", "").strip()
        original_response = input_data.get("response", {})
        
        # 如果沒有 response，可能是直接文字
        if not original_response and "text" in input_data:
            original_response = input_data.get("text", "")
        
        # 載入全域優化器
        from final_global_optimizer import optimize_for_openclaw
        
        # 優化回覆
        optimized_response = optimize_for_openclaw(original_response, user_input)
        
        # 準備輸出
        if isinstance(optimized_response, dict):
            output = optimized_response
        else:
            output = {
                "text": str(optimized_response),
                "metadata": {
                    "globally_optimized": True,
                    "optimization_type": "text_only"
                }
            }
        
        # 輸出結果
        print(json.dumps(output, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            "text": f"❌ 優化錯誤: {str(e)[:30]}",
            "metadata": {"error": str(e)}
        }
        print(json.dumps(error_result, ensure_ascii=False))

if __name__ == "__main__":
    main()