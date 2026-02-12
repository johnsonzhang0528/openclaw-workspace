# Telegram Bot 設定指南

## 步驟 1: 創建 Telegram Bot

### 1.1 開啟 Telegram
1. 在 Telegram 中搜尋 `@BotFather`
2. 點擊開始對話

### 1.2 創建新 Bot
發送以下指令給 @BotFather：

```
/newbot
```

### 1.3 設定 Bot 名稱
1. 輸入 Bot 名稱（例如：`OpenClaw Monitor Bot`）
2. 輸入 Bot 使用者名稱（必須以 `bot` 結尾，例如：`openclaw_monitor_bot`）

### 1.4 獲取 Bot Token
成功創建後，@BotFather 會提供一個 Bot Token，格式如下：
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-ABCDEFGHI
```

**重要：請妥善保存此 Token，不要分享給他人！**

## 步驟 2: 獲取 Chat ID

### 2.1 個人聊天 ID
1. 在 Telegram 中搜尋你剛創建的 Bot
2. 發送任何訊息給 Bot（例如：`/start`）
3. 使用瀏覽器訪問以下網址（替換 `YOUR_BOT_TOKEN`）：
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. 在 JSON 回應中尋找 `"chat":{"id":123456789}`
5. 複製 `id` 的數值

### 2.2 群組聊天 ID
1. 將 Bot 加入群組
2. 在群組中發送任何訊息
3. 訪問相同的 API 網址：
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. 在 JSON 回應中尋找群組 ID（通常為負數，例如：`-1001234567890`）

## 步驟 3: 配置環境變數

### 3.1 編輯 .env 檔案
編輯監控系統目錄中的 `.env` 檔案：

```bash
cd /root/.openclaw/workspace/agent-monitoring-system
nano .env
```

### 3.2 設定 Token 和 Chat ID
找到以下兩行並替換為你的實際值：

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-ABCDEFGHI
TELEGRAM_CHAT_ID=1234567890
```

### 3.3 儲存並測試
儲存檔案後，測試配置：

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
print(f'✅ Bot Token: {token[:10]}...')
print(f'✅ Chat ID: {chat_id}')
"
```

## 步驟 4: 測試 Telegram 通知

### 4.1 手動測試
使用以下 Python 腳本測試 Telegram 通知：

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_test_message():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': '✅ OpenClaw 監控系統測試訊息\n系統已成功配置！',
        'parse_mode': 'HTML'
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print('✅ 測試訊息發送成功！')
    else:
        print(f'❌ 發送失敗: {response.text}')

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print('❌ 請先設定 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID')
    else:
        send_test_message()
```

### 4.2 使用監控系統測試
運行監控系統測試：

```bash
python3 test_monitoring.py module telegram_dashboard
```

## 步驟 5: Bot 權限設定（可選）

### 5.1 設定 Bot 指令
發送以下指令給 @BotFather：

```
/setcommands
```

選擇你的 Bot，然後發送指令列表：

```
monitor - 顯示監控儀表板
status - 顯示系統狀態
alerts - 顯示當前警報
help - 顯示幫助訊息
```

### 5.2 設定 Bot 隱私模式
如果 Bot 在群組中，建議設定隱私模式：

```
/setprivacy
```

選擇你的 Bot，然後選擇 `Disable` 讓 Bot 可以讀取所有群組訊息。

## 疑難排解

### 問題 1: Bot Token 無效
**症狀**: `401: Unauthorized` 錯誤
**解決方案**:
1. 確認 Token 是否正確複製（包含冒號）
2. 重新從 @BotFather 獲取 Token
3. 檢查 Token 是否有空格

### 問題 2: Chat ID 錯誤
**症狀**: `400: Bad Request` 錯誤
**解決方案**:
1. 確認 Chat ID 是否為數字（群組 ID 為負數）
2. 確保 Bot 已加入聊天
3. 在聊天中發送訊息後重新獲取 Chat ID

### 問題 3: 沒有收到訊息
**症狀**: API 回傳成功但沒有收到訊息
**解決方案**:
1. 檢查 Bot 是否被屏蔽
2. 確認 Chat ID 是否正確
3. 嘗試發送簡單文字訊息測試

### 問題 4: 權限不足
**症狀**: `403: Forbidden` 錯誤
**解決方案**:
1. 確保 Bot 有發送訊息的權限
2. 在群組中檢查 Bot 的管理員權限
3. 解除屏蔽 Bot

## 安全建議

### 1. Token 保護
- 不要將 Token 提交到版本控制系統
- 使用環境變數或密碼管理器儲存
- 定期更換 Token

### 2. 存取控制
- 限制 Bot 可存取的聊天
- 使用白名單控制可發送指令的用戶
- 定期審查 Bot 活動

### 3. 備份配置
- 備份 `.env` 檔案
- 記錄 Bot Token 和 Chat ID
- 保存 @BotFather 的對話記錄

## 進階設定

### 自定義 Bot 圖片
1. 發送 `/setuserpic` 給 @BotFather
2. 選擇你的 Bot
3. 上傳圖片（建議 150x150 像素）

### 設定 Bot 描述
```
/setdescription
```
輸入 Bot 描述，例如：
```
OpenClaw 系統監控機器人
即時監控系統狀態和資源使用情況
```

### 設定 Bot 關於資訊
```
/setabouttext
```
輸入關於資訊，例如：
```
OpenClaw Agent Monitoring System
版本: 1.0.0
```

## 支援與協助

如果遇到問題，請：

1. 檢查日誌檔案：`monitoring.log`
2. 查看錯誤訊息詳細資訊
3. 確認網路連線正常
4. 驗證 Telegram API 可用性

如需進一步協助，請聯繫系統管理員或參考官方文件。