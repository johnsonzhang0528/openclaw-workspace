# 技能模板

## 技能信息
- **名稱**：{{skill_name}}
- **版本**：1.0.0
- **作者**：{{author}}
- **描述**：{{description}}
- **分類**：{{category}}

## 市場信息
```yaml
marketplace:
  name: "{{skill_name}}"
  version: "1.0.0"
  author: "{{author}}"
  description: "{{description}}"
  tags: ["{{category}}"]
  dependencies: []
  min_openclaw_version: "2026.2.0"
  repository: "{{repository_url}}"
  documentation: "{{docs_url}}"
```

## 安裝要求
- OpenClaw 版本：2026.2.0 或更高
- Python 版本：3.8+
- 依賴套件：見 requirements.txt

## 檔案結構
```
{{skill_name}}/
├── SKILL.md              # 本文件
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

## 配置說明
```json
// openclaw.json 中的技能配置
{
  "skills": {
    "{{skill_name}}": {
      "enabled": true,
      "config": {
        // 技能特定配置
      }
    }
  }
}
```

## Telegram 命令
```
/{{command_prefix}} - {{skill_description}}
```

## 開發指南

### 1. 初始化技能
```bash
# 使用技能創建工具
python dev-tools/skill-builder.py create {{skill_name}}
```

### 2. 開發測試
```bash
# 運行測試
python -m pytest tests/

# 本地測試 Telegram 介面
python dev-tools/test-telegram.py {{skill_name}}
```

### 3. 打包部署
```bash
# 打包技能
python dev-tools/skill-builder.py package {{skill_name}}

# 安裝到系統
sudo python dev-tools/skill-builder.py install {{skill_name}}.tar.gz
```

## API 參考

### 核心函數
```python
def initialize(config: dict) -> bool:
    """初始化技能，返回是否成功"""
    pass

def handle_command(command: str, args: list, context: dict) -> dict:
    """處理命令，返回回應"""
    pass

def cleanup() -> None:
    """清理資源"""
    pass
```

### Telegram 介面
```python
def send_telegram_message(chat_id: str, text: str, buttons: list = None):
    """發送 Telegram 訊息"""
    pass

def create_inline_keyboard(buttons: list) -> dict:
    """創建 inline keyboard"""
    pass
```

## 錯誤處理

### 常見錯誤
1. **配置錯誤**：檢查 openclaw.json
2. **依賴錯誤**：運行 `pip install -r requirements.txt`
3. **權限錯誤**：檢查檔案權限

### 除錯模式
```bash
# 啟用詳細日誌
export OPENCLAW_DEBUG=1
openclaw gateway restart
```

## 更新日誌

### v1.0.0 (YYYY-MM-DD)
- 初始版本發布
- 基本功能實現
- Telegram 介面整合

## 貢獻指南
1. Fork 專案
2. 創建功能分支
3. 提交 Pull Request
4. 通過測試後合併

## 授權協議
MIT License

## 聯絡方式
- 問題回報：{{issues_url}}
- 討論區：{{forum_url}}
- 電子郵件：{{email}}