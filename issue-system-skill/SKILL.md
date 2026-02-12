# 議題追蹤系統技能

## 概述
智慧議題追蹤與管理系統，提供完整的 Telegram 互動介面。符合 MEMORY.md 中的議題系統規則，並整合閱讀成本優化功能。

## 功能特色
1. **完整的 Telegram 互動介面**
   - `/issue` 指令處理器
   - inline keyboard 管理系統
   - 議題狀態切換功能
   - 自動議題偵測

2. **智慧議題管理**
   - 自動偵測新議題
   - 議題狀態管理（開啟/關閉）
   - 討論記錄與摘要
   - 歷史議題查詢

3. **閱讀成本優化**
   - 符合 MEMORY.md 優化規則
   - 極簡化設計
   - 視覺化呈現
   - 資訊密度提升

## 安裝與設定

### 前置需求
- OpenClaw 工作環境
- Python 3.6+
- 議題系統核心模組 (`issue_system_main.py`)

### 安裝步驟
1. 將 `issue-system-skill/` 目複製到 OpenClaw 技能目錄
2. 確保議題系統核心模組可用
3. 在 OpenClaw 中註冊技能

### 快速測試
```bash
cd /root/.openclaw/workspace
python3 issue-system-skill/integrate_with_openclaw.py
```

## 使用方式

### Telegram 指令
- `/issue` - 查看當前議題列表
- `/issueHistory` - 查看歷史議題

### 互動操作
1. **點擊議題**（在列表中）→ 查看議題詳情
2. **操作按鈕**：
   - ✅ 關閉議題 - 結束討論並生成摘要
   - 🔄 重新開啟 - 重新開啟已關閉的議題
   - 📝 繼續討論 - 設定為當前討論議題
   - 📖 查看記錄 - 查看完整討論歷史

### 自動功能
- **自動議題偵測**：當對話主題轉換時自動建立新議題
- **自動摘要生成**：每次討論自動生成重點提要
- **自動狀態管理**：根據討論進度建議關閉議題

## 技術架構

### 檔案結構
```
issue-system-skill/
├── main.py                    # 技能主程式
├── integrate_with_openclaw.py # OpenClaw 整合
├── SKILL.md                   # 技能說明文件
└── README.md                  # 使用說明
```

### 依賴模組
- `issue_system_main.py` - 議題系統核心
- `issue_telegram_integration.py` - Telegram 整合
- `issue_manager.py` - 議題管理
- `issue_telegram_handler.py` - Telegram 處理器

### 資料儲存
- `issues/` - 議題儲存目錄
- `issues_index.json` - 議題索引
- `system_state.json` - 系統狀態

## 配置選項

### 系統設定（issues_index.json）
```json
{
  "settings": {
    "similarity_threshold": 0.3,    // 主題相似度閾值
    "auto_detection": true,         // 自動偵測開關
    "current_issue_id": null        // 當前議題ID
  }
}
```

### 優化設定
- **閱讀成本優化**：自動啟用
- **回應簡化**：移除冗餘文字
- **時間顯示**：相對時間格式
- **按鈕優化**：圖示+簡短文字

## 開發指南

### 擴展功能
1. **新增議題操作**：在 `issue_telegram_handler.py` 中添加處理函數
2. **自訂按鈕**：修改按鈕生成邏輯
3. **優化規則**：調整 `optimize_response_text` 函數

### 測試方法
```python
# 單元測試
python3 issue-system-skill/main.py

# 整合測試
python3 issue-system-skill/integrate_with_openclaw.py

# 功能測試
python3 test_issue_system.py
```

### 除錯技巧
1. 檢查日誌輸出
2. 驗證議題檔案完整性
3. 測試 Telegram 按鈕回應
4. 監控系統狀態

## 常見問題

### Q: 議題未自動建立
A: 檢查 `auto_detection` 設定，調整 `similarity_threshold`

### Q: 按鈕無反應
A: 確保 callback_data 格式正確，檢查 Telegram 整合

### Q: 回應文字過長
A: 閱讀成本優化已自動處理，可調整優化規則

### Q: 資料遺失
A: 所有資料儲存在 `issues/` 目錄，定期備份 `issues_index.json`

## 版本記錄

### v1.0.0 (2026-02-12)
- 初始版本發布
- 完整的 Telegram 互動介面
- 議題狀態管理功能
- 閱讀成本優化整合
- OpenClaw 技能標準化

## 聯絡與支援
- 問題回報：OpenClaw 議題系統
- 功能建議：透過議題系統追蹤
- 技術支援：檢查系統日誌和錯誤訊息

---

**技能狀態**：✅ 已就緒  
**測試狀態**：✅ 通過基本測試  
**生產環境**：✅ 可部署  
**維護狀態**：🟢 活躍維護