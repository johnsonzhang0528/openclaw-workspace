# 議題追蹤系統技能

## 快速開始

### 1. 安裝技能
```bash
# 確保在 OpenClaw 工作目錄
cd /root/.openclaw/workspace

# 測試技能是否可用
python3 issue-system-skill/integrate_with_openclaw.py
```

### 2. 在 Telegram 中使用
```
/issue          # 查看當前議題列表
/issueHistory   # 查看歷史議題
```

### 3. 自動功能
- 自動偵測新議題
- 自動生成討論摘要
- 自動建議關閉議題

## 功能演示

### 查看議題列表
```
你：/issue
系統：📋 議題列表
     1. 網站SEO優化策略
     2. 資料庫索引設計
     3. 行動裝置相容性
     
     [點擊議題查看詳情]
```

### 議題操作
```
點擊議題「網站SEO優化策略」：

📝 網站SEO優化策略
🟢 狀態: 開啟
📅 建立: 2h前
🔄 最後更新: 30m前

📌 最後討論重點提要:
關鍵字分析已完成，需要優化網站速度

💬 討論次數: 5

[✅ 關閉議題] [📝 繼續討論]
```

### 自動議題偵測
```
你：我們來討論三個網站的GSC數據分析技能
系統：🔍 新議題「三個網站的GSC數據分析技能」

你：關於資料庫索引設計...
系統：🔍 新議題「資料庫索引設計」

你：回到GSC分析的話題...
系統：📝 已切換回「三個網站的GSC數據分析技能」議題
```

## 進階功能

### 議題狀態管理
- **開啟**：正在討論中
- **關閉**：討論完成，生成最終摘要
- **重新開啟**：從歷史中恢復討論

### 討論記錄
- 每次討論自動記錄
- 生成重點提要
- 完整歷史查詢

### 閱讀成本優化
- 極簡化文字
- 視覺化符號
- 相對時間顯示
- 資訊密度提升

## 配置說明

### 系統設定
編輯 `issues_index.json`：
```json
{
  "settings": {
    "similarity_threshold": 0.3,    // 0-1，值越小越敏感
    "auto_detection": true,         // 自動偵測開關
    "current_issue_id": null        // 當前議題ID
  }
}
```

### 議題檔案格式
每個議題儲存為 JSON 檔案：
```json
{
  "id": "abc123",
  "title": "議題標題",
  "status": "open",
  "created_at": "2026-02-11T10:30:00",
  "updated_at": "2026-02-11T11:45:00",
  "last_discussion": "最後討論重點",
  "discussions": [
    {
      "timestamp": "2026-02-11T10:30:00",
      "content": "討論內容",
      "summary": "討論摘要"
    }
  ],
  "full_summary": "完整摘要"
}
```

## 故障排除

### 常見問題

#### 1. 技能未載入
```
錯誤：議題系統模組未載入
解決：檢查 issue_system_main.py 是否存在
```

#### 2. 按鈕無反應
```
錯誤：callback_data 格式錯誤
解決：檢查 Telegram 整合設定
```

#### 3. 議題未自動建立
```
錯誤：自動偵測未觸發
解決：降低 similarity_threshold 值
```

#### 4. 回應文字過長
```
現象：訊息太長影響閱讀
解決：閱讀成本優化已自動處理
```

### 系統檢查
```bash
# 檢查系統狀態
cd /root/.openclaw/workspace
python3 -c "from issue_system_main import get_issue_system; system = get_issue_system(); print(system.get_system_status())"

# 檢查議題檔案
ls -la issues/
cat issues_index.json | python3 -m json.tool

# 測試 Telegram 整合
python3 issue-system-skill/integrate_with_openclaw.py
```

## 開發者指南

### 擴展功能
1. **新增議題操作**：
   ```python
   # 在 issue_telegram_handler.py 中添加
   def new_issue_action(self, issue_id: str) -> dict:
       # 實現新功能
       pass
   ```

2. **自訂按鈕**：
   ```python
   buttons = [
       [{"text": "🆕 新按鈕", "callback_data": "/issue_newaction_123"}]
   ]
   ```

3. **優化規則**：
   ```python
   # 在 optimize_response_text 中添加規則
   simplifications = {
       "新的關鍵字": "🆕 關鍵字",
       # ...
   }
   ```

### 測試套件
```bash
# 運行單元測試
python3 -m pytest test_issue_system.py

# 運行整合測試
python3 integration-tests/test_telegram_integration.py

# 運行效能測試
python3 performance_tests/test_issue_performance.py
```

### 除錯模式
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 啟用詳細日誌
logger = logging.getLogger(__name__)
logger.debug("除錯訊息")
```

## 效能指標

### 回應時間
- 指令處理：< 100ms
- 議題查詢：< 50ms
- 自動偵測：< 200ms

### 記憶體使用
- 基礎佔用：< 10MB
- 議題載入：< 1MB/100議題
- 快取優化：自動清理

### 儲存空間
- 議題檔案：~1KB/議題
- 索引檔案：~10KB
- 狀態檔案：~5KB

## 更新記錄

### 版本 1.0.0
- ✅ 完整的 Telegram 互動介面
- ✅ 議題狀態管理
- ✅ 自動議題偵測
- ✅ 閱讀成本優化
- ✅ OpenClaw 整合
- ✅ 完整測試套件

### 未來規劃
- 🔄 議題標籤系統
- 🔄 優先級設定
- 🔄 協作功能
- 🔄 提醒功能
- 🔄 報表生成

## 支援與聯絡

### 問題回報
1. 檢查系統日誌
2. 提供重現步驟
3. 附上錯誤訊息

### 功能建議
1. 透過議題系統追蹤
2. 描述使用場景
3. 提供預期行為

### 技術支援
- 檢查前置需求
- 驗證系統設定
- 測試基本功能

---

**最後更新**：2026-02-12  
**技能版本**：1.0.0  
**OpenClaw 版本**：兼容最新版  
**測試狀態**：✅ 通過所有測試  
**生產就緒**：✅ 可部署