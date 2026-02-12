# 技能市集瀏覽器

## 功能概述
- 🔍 搜索和瀏覽 OpenClaw 技能
- 📦 一鍵安裝/卸載技能
- ⭐ 熱門技能推薦
- 🔄 自動更新檢查

## 安裝狀態
✅ 技能市集已成功安裝

## 使用方法

### Telegram 命令
1. `/skills` - 打開技能市集主選單
2. `/skill_search [關鍵字]` - 搜索技能
3. `/skill_install [技能名稱]` - 安裝技能
4. `/skill_list` - 列出已安裝技能
5. `/skill_update` - 更新技能

### 互動操作
- 使用 inline keyboard 按鈕進行操作
- 點擊技能名稱查看詳情
- 點擊安裝按鈕一鍵安裝

## 檔案位置
- 主程式: `/root/.openclaw/workspace/skills-marketplace/`
- 資料儲存: `/root/.openclaw/workspace/skills-marketplace/data/`
- 日誌檔案: `/root/.openclaw/logs/skills-marketplace.log`

## 測試安裝
運行測試腳本確認功能正常：
```bash
cd /root/.openclaw/workspace/skills-marketplace
python3 test_integration.py
```

## 故障排除
1. **安裝失敗**: 檢查網路連接和權限
2. **搜索無結果**: 嘗試不同關鍵字
3. **更新失敗**: 檢查技能版本兼容性

## 支援
如有問題，請查看日誌檔案或重新運行安裝腳本。

---
安裝時間: $(date)
版本: 1.0.0
