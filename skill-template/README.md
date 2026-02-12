# {{skill_name}}

{{description}}

## 功能特色

- **功能1**: 簡要描述
- **功能2**: 簡要描述
- **功能3**: 簡要描述

## 快速開始

### 安裝

1. 下載技能套件
2. 安裝到 OpenClaw:
   ```bash
   sudo python dev-tools/skill-builder.py install {{skill_name}}.tar.gz
   ```
3. 重啟 OpenClaw:
   ```bash
   openclaw gateway restart
   ```

### 使用

基本命令:
```
/{{command_prefix}} help - 顯示幫助
/{{command_prefix}} status - 顯示狀態
/{{command_prefix}} config - 顯示配置
```

## 配置

在 `openclaw.json` 中添加以下配置:

```json
{
  "skills": {
    "{{skill_name}}": {
      "enabled": true,
      "config": {
        "telegram_enabled": true,
        "data_path": "/root/.openclaw/workspace/{{skill_name}}"
      }
    }
  }
}
```

## 開發

### 環境設置

```bash
# 克隆專案
git clone {{repository_url}}

# 安裝依賴
pip install -r requirements.txt

# 運行測試
python -m pytest tests/
```

### 專案結構

```
{{skill_name}}/
├── SKILL.md              # 技能文檔
├── package.json          # 技能配置
├── requirements.txt      # Python 依賴
├── main.py              # 主程式入口
├── config.py            # 配置管理
├── utils.py             # 工具函數
├── telegram_ui.py       # Telegram 介面
├── tests/               # 測試檔案
│   ├── test_main.py
│   └── test_telegram.py
└── assets/              # 資源檔案
    ├── icons/
    └── templates/
```

### 添加新功能

1. 在 `main.py` 中添加新的命令處理方法
2. 在 `telegram_ui.py` 中添加對應的 UI 處理
3. 添加測試案例
4. 更新文檔

## API 參考

### 核心方法

```python
def handle_command(command: str, args: list, context: dict) -> dict:
    """處理命令"""
    pass
```

### 回應格式

```python
{
    'success': True/False,
    'message': '回應訊息',
    'format': 'text/markdown/html/keyboard',
    'data': {},  # 可選，額外數據
    'error': '錯誤代碼'  # 可選，錯誤時使用
}
```

## 貢獻

1. Fork 專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 授權

MIT License

## 聯絡

- 作者: {{author}}
- 問題回報: {{issues_url}}
- 討論區: {{forum_url}}
- 電子郵件: {{email}}