# Git 版本管理指南

## 基本設定

Git 已配置完成：
- **用戶名稱**：(見 git config)
- **郵箱**：(見 git config)
- **工作目錄**：/root/.openclaw/workspace

## 常用指令

### 查看狀態
```bash
git status
```

### 添加檔案
```bash
git add <檔案名稱>
git add .          # 添加所有變更
```

### 提交變更
```bash
git commit -m "提交訊息"
```

### 查看歷史
```bash
git log --oneline -10  # 最近10次提交
git log --graph        # 圖形化顯示
```

### 分支操作
```bash
git branch                    # 查看分支
git branch <分支名稱>         # 創建分支
git checkout <分支名稱>       # 切換分支
git merge <分支名稱>          # 合併分支
```

### 遠端倉庫（可選）
```bash
# 添加遠端倉庫
git remote add origin <遠端倉庫URL>

# 推送變更
git push -u origin master

# 拉取更新
git pull origin master
```

## 工作流程建議

1. **日常開發**：
   ```bash
   git status          # 檢查狀態
   git add .           # 添加變更
   git commit -m "描述變更內容"
   ```

2. **功能開發**：
   ```bash
   git branch feature-new-skill  # 創建功能分支
   git checkout feature-new-skill # 切換到功能分支
   # ... 開發功能 ...
   git add . && git commit -m "完成新技能開發"
   git checkout master           # 切換回主分支
   git merge feature-new-skill   # 合併功能
   ```

3. **定期備份**：
   ```bash
   # 如果有遠端倉庫
   git push origin master
   ```

## 注意事項

1. **`.gitignore`** 已配置，會自動忽略：
   - Python 快取檔案
   - 虛擬環境
   - 日誌檔案
   - 資料庫檔案
   - 敏感配置文件

2. **記憶體檔案**：
   - `memory/*.md` 檔案已被忽略
   - 重要設定請手動備份

3. **提交頻率**：
   - 建議每天至少提交一次
   - 每次功能完成後提交
   - 重大變更前提交

## 故障排除

### 撤銷變更
```bash
# 撤銷未暫存的變更
git checkout -- <檔案名稱>

# 撤銷暫存的變更
git reset HEAD <檔案名稱>

# 撤銷最近一次提交
git reset --soft HEAD~1
```

### 查看差異
```bash
git diff              # 查看未暫存的變更
git diff --staged     # 查看已暫存的變更
```

## 進階功能

### 標籤管理
```bash
git tag v1.0.0        # 創建標籤
git push --tags       # 推送標籤
```

### 暫存變更
```bash
git stash             # 暫存當前變更
git stash pop         # 恢復暫存的變更
```

---

**提示**：Git 是強大的版本控制工具，建議定期提交並保持提交訊息的清晰性。