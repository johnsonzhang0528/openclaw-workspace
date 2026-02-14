# TodoList - 功能開發需求清單

## 規則說明
- 當使用者在 Telegram 提出新功能開發需求時，將需求記錄在此檔案
- 僅記錄需求描述，不透過 OpenClaw 直接開發功能
- 供後續手動開發參考

## 需求清單

### 待處理
#### 1) 圖片內容辨識與分析功能
**提出時間：** 2026-02-14 15:39
**來源：** 使用者直接提出
**優先級：** 中  
**狀態：** 待規劃

**需求描述：**
- 讓 OpenClaw 能夠辨識用戶上傳的圖片內容並加以分析
- 支援多種圖片格式（JPEG、PNG等）
- 提供結構化的分析結果

**具體功能：**
1. **圖片內容辨識**
   - 文字辨識（OCR）：提取圖片中的文字內容
   - 物件辨識：識別圖片中的物體、場景
   - 圖表分析：分析圖表、數據視覺化內容
   - 文件分析：辨識文件、表格、圖形

2. **分析功能**
   - 數據提取：從圖表中提取數值數據
   - 趨勢分析：分析圖表中的趨勢模式
   - 內容摘要：生成圖片內容的文字摘要
   - 分類標籤：為圖片添加分類標籤

3. **整合應用**
   - Telegram 圖片訊息自動分析
   - 批量圖片處理功能
   - 分析結果儲存與查詢
   - 自定義分析模板

**技術考量：**
- 圖像辨識 API 選擇（OpenAI Vision、Google Vision、本地模型）
- 成本控制（API 使用量管理）
- 處理效能（響應時間、並發處理）
- 錯誤處理（圖片質量問題、辨識失敗）

**潛在應用場景：**
- 網站數據報表分析
- 用戶上傳內容審核
- 自動化數據輸入
- 內容分類與標記

#### 2) 自動化賺錢系統設計
**提出時間：** 2026-02-14 14:00
**來源：** 使用者直接提出
**優先級：** 高  
**狀態：** 需求收集階段

**需求描述：**
- 低成本、全自動化、不需人工維運
- 有效賺取利潤的賺錢系統
- 透過 OpenClaw 進行任務執行

**需要收集的資訊：**
1. **預算範圍**：每月可投入資金
2. **技術能力**：程式/自動化經驗程度
3. **時間投入**：初期開發與後續維護時間
4. **風險承受度**：可承受的風險等級
5. **期望月收益**：目標每月利潤
6. **已有資源**：伺服器、API、帳號等資源

**潛在方案方向：**
- 網路爬蟲與數據販售
- API 服務提供
- 內容自動生成與販售
- 電商自動化
- 社交媒體自動化營利
- 加密貨幣/股票自動交易

**技術考量：**
- 全自動化程度
- 成本控制機制
- 風險管理系統
- 收益追蹤與報告

#### 2) 多租戶功能擴展（進階版）
**提出時間：** 2026-02-13 17:51
**來源：** 使用者直接提出
**優先級：** 中  
**狀態：** 待規劃

**需求描述：**
- 在現有多租戶系統（基礎版）基礎上進一步擴展功能
- 支援更多租戶隔離場景
- 增強租戶間資源分配與管理

**具體功能：**
1. **租戶資源配額管理**
   - CPU/記憶體/磁碟使用限制
   - API 呼叫頻率限制
   - 並發會話數限制

2. **租戶計費系統**
   - 使用量追蹤與計費
   - 訂閱方案管理
   - 發票與付款整合

3. **租戶自助管理介面**
   - 租戶專屬控制台
   - 資源使用監控
   - 配置調整功能

4. **租戶隔離強化**
   - 資料庫隔離
   - 檔案系統隔離
   - 網路隔離

5. **租戶遷移工具**
   - 租戶資料匯出/匯入
   - 租戶合併/拆分
   - 跨實例遷移

**技術考量：**
- 與現有 RBAC 權限系統整合
- 保持向後相容性
- 效能影響最小化

**驗收標準（DoD）：**
- 支援至少 100 個租戶同時運作
- 租戶間資源隔離完整
- 管理介面操作流暢
- 計費系統準確可靠

---

#### 2) 伺服器與平台安全防護
**整併來源：** 伺服器安全防護系統  
**優先級：** 高（安全）  
**狀態：** 待規劃

**完成成果：**
1. **租戶管理 `tenant_manager.py`**
   - 租戶識別：`tenant_id = telegram:{chat_id}`，支援私聊/群組/頻道
   - 租戶註冊表 `tenants.json`（含備份 `.bak`，毀損時自動恢復）
   - 租戶目錄隔離：`/root/.openclaw/monitoring/tenants/{tenant_id}/`
   - 每租戶獨立 `state.json`、`audit.log`、`error_events.jsonl`、`config.json`
   - 自動從 `.env` 遷移原始單一租戶（首次啟動零配置）
   - 租戶自訂設定：閾值、冷卻時間、功能開關（dashboard/alerts/self_heal/restart_button）
2. **RBAC 權限控制 `rbac.py`**
   - 四層角色：`owner > admin > member > viewer`
   - 18 項權限矩陣，每項對應最低角色
   - 高風險操作標記：`restart_gateway`、`delete_data`、`manage_tenants`、`manage_rbac`、`modify_config`
   - RBAC 整合至 `handle_restart_callbacks()`：未授權使用者按重啟鈕會被拒絕並記錄
   - 自動從 `.env` 遷移 owner 角色（首次啟動）
3. **審計日誌 `audit.py`**
   - Append-only JSONL 格式，每租戶獨立 `audit.log`
   - 記錄類型：`config_change`、`config_rollback`、`restart`、`role_change`、`permission_denied`、`self_heal`
   - 含操作者、時間、詳情、結果
4. **配置治理 `config_governance.py`**
   - 配置變更流程：驗證 schema → 備份舊值 → 套用 → 健康檢查 → 失敗自動回滾
   - 版本化配置：`config-v{n}.json`，每次變更產生完整差異記錄
   - Schema 驗證：型別檢查 + 範圍檢查（如 CPU 閾值 50-99%）
   - 支援回滾至任意歷史版本
5. **健康引擎多租戶整合**
   - 全域採集一次、分發給所有租戶（不重複採集）
   - 自癒（Gateway 重啟）全域只執行一次，避免多租戶下重複重啟
   - 每租戶獨立閾值、冷卻時間、告警過濾
   - 全域 `monitoring_state.json` 精簡化（僅含快照/分數/等級），供 `/monitor` 快速讀取
6. **衝突修復與向後相容**
   - `proactive_alerts.py` 已棄用（加入 `sys.exit(0)` 防護）
   - `send_restart_notification.py` 已改為多租戶扇出通知
   - `evaluate_alerts()` 支援租戶自訂閾值參數
   - `tenants.json` 毀損保護：自動從 `.bak` 備份恢復

**驗收標準（DoD）：** ✅ 全部通過
- ✅ 租戶狀態完全隔離，各租戶目錄獨立
- ✅ 未授權使用者執行高風險命令時被拒絕並記錄（RBAC + audit.log）
- ✅ 配置套用失敗可自動回滾（apply → health_check → rollback 流程已驗證）
- ✅ 全域自癒不因多租戶重複執行
- ✅ 向後相容：`monitor_snapshot.py` 正常運作（~170ms 回應）
- ✅ 註冊表毀損時可從備份恢復（已驗證）

---

#### 2) 可觀測性、監控效能與健康檢查
**整併來源：** /monitor 指令效能優化、系統效能優化與健康檢查、錯誤追蹤與報告、/reset 後自動推送（日報/監控）  
**優先級：** 高  
**狀態：** ✅ 已完成 (2026-02-13)

**目標：**
- 讓 `/monitor` 快速、完整、可追蹤
- 建立統一健康評分與告警、錯誤追蹤機制

**完成成果：**
1. **統一健康引擎 `health_engine.py`**
   - 平行採集 7 項指標（CPU/RAM/Disk/Load/Gateway/Subagent/Cron），約 2.7 秒
   - 統一狀態檔 `monitoring_state.json`（v2 schema），合併舊 proactive_alert + unified_dashboard 兩套狀態
   - 健康分數 0-100，權重化計算（Gateway 30%、CPU 15%、RAM 15%、Disk 10%、Load 10%、Cron 10%、Error 10%）
   - A/B/C/D/F 等級制
2. **告警系統統一**
   - 狀態轉換偵測（僅在變化時告警，避免重複）
   - 每類告警獨立冷卻時間（gateway 120s、其他 600s）
   - Inline keyboard 快捷操作（重啟、查日誌、效能概覽）
3. **自癒機制**
   - Gateway 停止時自動重啟（最多 3 次，間隔 5 分鐘）
   - 連續失敗後停止自癒，等待人工介入
   - 恢復後自動重設計數器
4. **錯誤追蹤**
   - 錯誤事件寫入 `error_events.jsonl`（append-only）
   - 記憶體中保留最近 50 筆摘要
   - 每日計數自動歸零
5. **/monitor 快速回應**
   - `monitor_snapshot.py` 直接讀取快取，回應時間 ~170ms
   - 已建立 skill `system-monitor`（SKILL.md）供 OpenClaw agent 使用
6. **Cron 遷移**
   - `run_health_engine.sh` 取代 `run_every_30s.sh`
   - 自帶 D-Bus 環境變數，每分鐘執行兩次（0s + 30s）
   - 舊狀態自動遷移（dashboard_message_id、last_update_id、last_alerts）

**驗收標準（DoD）：** ✅ 全部通過
- ✅ `/monitor` 平均回應時間 ~170ms（目標 < 3 秒）
- ✅ 監控資訊欄位完整率 100%（7 項指標全覆蓋）
- ✅ 告警冷卻 + 狀態轉換偵測，消除重複通知
- ✅ 健康分數 100/A（正常運行時）
- ✅ Cron 自動執行，30 秒更新一次

---

#### 3) 日誌治理、備份與災難恢復
**整併來源：** OpenClaw 日誌管理與自動備份系統優化、GitHub 遠端備份整合系統  
**優先級：** 高  
**狀態：** ✅ 已完成 (2026-02-13)

**目標：**
- 建立可長期運行的日誌與備份體系，確保可還原、可驗證、可稽核

**完成成果：**
1. **日誌治理引擎 `log_governance.py`**
   - 統一管理 13 個日誌來源（核心/效能/審計/暫存/會話/Gateway/Cron）
   - 六級保留策略：核心 30 天、效能 7 天、審計 90 天、暫存 3 天、會話 14 天、Gateway 14 天
   - Copytruncate 語意：壓縮/輪轉時截斷原檔而非刪除/重命名，保護正在寫入的行程（如 health_engine >> 重導向）
   - 單檔大小上限輪轉（超過 max_size_mb 自動截斷）
   - gzip 壓縮（compresslevel=6）保留原始時間戳
   - `--dry-run` 模式：預覽不執行
   - `--report` 模式：磁碟使用報告（含 Telegram HTML 格式化）
2. **備份引擎 `backup_engine.py`**
   - **L1 本地快照**：tar.gz 壓縮，含 SHA-256 完整性校驗
     - 69 檔 / 735 KB 原始 → 193 KB 壓縮（~35ms）
     - 保留最新 7 份，自動清理舊備份
     - 每份備份附帶 manifest JSON（檔案清單、逐檔 SHA-256、時間戳）
   - **L2 遠端推送**：增量 git commit + push 至 GitHub HTTPS remote
     - 自動確保 .gitignore 包含 12 項敏感檔案排除規則
   - CLI 子命令：`backup / verify / restore / list / status / push / full`
3. **災難恢復**
   - `restore` 指令：驗證 → 解壓 → 逐檔還原，支援 `--dry-run` 預覽
   - 還原目標可指定任意目錄（沙盒測試）
   - 備份驗證：SHA-256 checksum + tar 成員數量交叉比對
4. **審計日誌保留策略 `audit.py`**
   - 新增 `enforce_retention()`：移除超過 90 天的審計記錄
   - 原子寫入（tmp → replace）避免截斷時資料遺失
   - 整合至排程備份流程（每日自動執行）
5. **健康引擎整合**
   - `/monitor` 儀表板新增 💾 備份區段（最後備份時間、可用份數、失敗次數）
   - 備份狀態讀取已最佳化：直接讀 `backup_state.json`（單次 I/O），不實例化 BackupEngine
6. **排程與衝突修復**
   - `run_backup.sh` + cron `0 22 * * *`（每日 06:00 GMT+8）
   - 流程：本地備份 → 驗證 → 遠端推送 → 日誌輪轉 → 審計記錄
   - 修復 CRITICAL：壓縮/輪轉改用 copytruncate 避免 health_engine shell `>>` 寫入遺失
   - 修復 WARNING：BackupEngine 不再在 render_dashboard 中實例化（改讀快取）
   - 修復 WARNING：gitignore 確保規則擴展至 12 項（含 identity/、credentials/、*.pem 等）

**備份內容（69 檔）：**
- 監控狀態：monitoring_state.json、tenants.json、rbac.json、global_snapshot.json
- 租戶資料：state.json、audit.log、config.json、config-v*.json（全租戶）
- 工作區腳本：*.py、*.sh、*.md
- 核心配置：openclaw.json、cron/jobs.json、shortcuts/、subagents/
- 排除：.env（token）、identity/、credentials/、sessions/（可重建）

**驗收標準（DoD）：** ✅ 全部通過
- ✅ 日誌空間可控（13 來源 × 各有保留策略，copytruncate 不影響運行中行程）
- ✅ 本地備份可在 35ms 內完成，SHA-256 驗證通過
- ✅ 災難恢復 dry-run 成功（69 檔可還原）
- ✅ 備份驗證自動告警（consecutive_failures 追蹤）
- ✅ Cron 排程已安裝（每日 06:00 GMT+8）
- ✅ 儀表板顯示備份狀態（🟢 最後: timestamp, N 份可用）

---

#### 4) Telegram 控制台與操作體驗優化
**整併來源：** Telegram 主控面板系統、Telegram 底部固定選單功能、Telegram Inline Keyboard 主控面板（互動部分）  
**優先級：** 中  
**狀態：** ✅ 已完成 (2026-02-13)

**目標：**
- 以 inline keyboard 提供接近固定選單的操作體驗
- 降低指令記憶成本，提升常用任務可達性

**完成成果：**
1. **UI 元件庫 `telegram_ui.py`**
   - callback_data 編碼/解碼（格式：`m:{page}:{action}:{arg}`，全部 < 64 bytes）
   - 8 組鍵盤佈局：主選單、監控、系統、備份、設定、日誌、返回、重啟確認
   - 7 個靜態頁面產生器（主面板、子選單、確認頁、說明頁）
   - 10 個動態內容產生器（效能詳情、健康檢查、備份狀態/列表、設定/變更紀錄、磁碟報告、系統資訊等）
   - 訊息截斷安全機制（4000 字元限制，防止 Telegram 4096 上限）
   - Bot 指令註冊清單（/menu、/monitor、/help）
2. **選單處理器 `menu_handler.py`**
   - `/menu`、`/start` → 主控面板（inline keyboard）
   - `/monitor` → 健康儀表板
   - `/help` → 指令說明
   - 所有導航使用 editMessageText 更新原訊息（edit-in-place），避免洗版
   - 高風險操作（重啟 Gateway）需二次確認
   - 備份操作（立即備份、驗證）即時執行並回報結果
   - 審計日誌記錄所有高風險操作
3. **主控面板 IA（資訊架構）**
   - `/menu` → 主面板（6 大功能區）
   - 📊 監控中心：健康儀表板、效能詳情、最近告警
   - 🔧 系統操作：重啟 Gateway（含確認）、最近日誌、健康檢查
   - 💾 備份管理：立即備份、驗證備份、備份列表、備份狀態
   - ⚙️ 設定管理：查看設定、變更紀錄
   - 📝 日誌報告：磁碟使用報告
   - ℹ️ 系統資訊：Kernel、運行時間、角色、版本
4. **health_engine.py 整合**
   - `getUpdates` 擴展為每次執行都輪詢（不限於 Gateway 停機時）
   - `allowed_updates` 新增 `"message"`，接收 /指令
   - `TelegramSender.edit()` 支援 `keyboard` 參數（inline keyboard）
   - `TelegramSender.set_my_commands()` 新增方法
   - `_process_updates()` 統一路由：menu callback → menu_handler、/restart → legacy handler、/logs 等 → info handler
   - `_ensure_bot_commands()` 一次性註冊 Bot 指令選單
   - 舊版 `handle_restart_callbacks()` 已移除（dead code cleanup）
5. **RBAC 權限整合**
   - 每個選單操作前驗證權限
   - /menu → `view_menu`（viewer）
   - 監控頁面 → `view_dashboard`（viewer）
   - 系統日誌 → `view_logs`（member）
   - 健康檢查 → `view_health`（viewer）
   - 重啟 → `restart_gateway`（admin）
   - 備份操作 → `manage_backup`（admin）
   - 設定查看 → `view_config`（member）
   - /exec → `exec_command`（admin）+ 白名單限制
6. **衝突修復**
   - 🔴 修復：自癒計數器 key 不匹配（`_do_restart` 錯用 `self_heal_attempts`，改為 `reset_self_heal_on_recovery()`）
   - ⚠️ 修復：`/exec` 缺少 RBAC 檢查（新增 `exec_command` 權限驗證）
   - ⚠️ 修復：健康檢查/備份狀態/磁碟報告缺少 RBAC（統一新增）
   - ✅ 清理：移除 `handle_restart_callbacks()` dead code
   - ✅ 驗證：dashboard 與 menu 使用不同 message_id，無干擾
   - ✅ 驗證：所有 callback 都有 answerCallbackQuery 回應
   - ✅ 驗證：無循環匯入（跨模組全部 lazy import）
7. **向後相容**
   - 舊版告警按鈕（/restart、/logs、/health、/tasks、/perf、/exec df -h）全部正常運作
   - `TelegramSender.edit()` 的 `keyboard` 參數預設 `None`，不影響現有呼叫
   - Dashboard 置頂訊息每 30 秒更新機制不受影響

**驗收標準（DoD）：** ✅ 全部通過（49/49 測試）
- ✅ 常用操作可在 2~3 次點擊內完成
- ✅ 所有 27 個 callback_data 均在 64-byte 限制內（max: 15 bytes）
- ✅ 所有子選單有返回按鈕，導航完整
- ✅ 高風險操作有 RBAC 攔截 + 二次確認
- ✅ editMessageText 導航不產生重複訊息
- ✅ Bot 指令選單已註冊（/menu、/monitor、/help）
- ✅ getUpdates 每次執行都輪詢，選單隨時可用
- ✅ 舊版告警按鈕向後相容

---

#### 5) 伺服器與平台安全防護
**整併來源：** 伺服器安全防護系統  
**優先級：** 高（安全）  
**狀態：** 待規劃

**目標：**
- 建立平台、主機、應用三層防護與事件應變機制

**實作細節：**
1. **平台層（Hetzner）**
   - 防火牆最小開放原則（僅必要埠）
   - 啟用 DDoS 相關保護與流量觀測
2. **系統層（Linux）**
   - SSH 強化（停用密碼登入、限制來源、Fail2ban）
   - 自動安全更新、必要服務最小化
   - 審計與存取紀錄保存
3. **應用層（OpenClaw/Telegram）**
   - Token/金鑰改為環境變數與權限控管
   - 指令 allowlist、管理命令二次確認
   - 輸入驗證、防注入、防路徑穿越
4. **監控與應變**
   - 建立攻擊事件告警分級（P1/P2/P3）
   - 明確 Runbook：偵測、隔離、復原、事後檢討

**驗收標準（DoD）：**
- 外部掃描僅暴露必要服務
- 高風險事件可在 SLA 內被偵測與通報
- 完成一次攻防演練與復盤

---

#### 6) API Token 成本與效率治理
**整併來源：** API Token 使用效率優化分析  
**優先級：** 中  
**狀態：** ✅ 已完成 (2026-02-13)

**目標：**
- 降低不必要 token 消耗，建立持續可追蹤的成本治理

**完成成果：**
1. **Token 追蹤引擎 `token_tracker.py`**
   - 增量式 Session JSONL 掃描器：基於檔案 byte offset 讀取，跨次執行持久化
   - 多模型計價：deepseek-chat（input $0.27/1M、output $1.10/1M、cache_read $0.07/1M、cache_write $0.27/1M）、deepseek-reasoner
   - 資料聚合：DailyBucket（每日）、HourlyBucket（每小時）、MonthSummary（每月）
   - 快取命中率計算：`cache_read / (input + cache_read)` 百分比
   - 預算管理：每日/每月上限，三級告警門檻（70%/90%/100%）
   - 狀態檔：`/root/.openclaw/monitoring/token_tracker_state.json`（已納入備份）
2. **Token 治理模組 `token_governance.py`**
   - `run_token_check(sender)` — 供 health_engine.py 每 30 秒呼叫，增量掃描 + 預算檢查
   - 預算告警回滾機制：Telegram 發送失敗時回滾 `alerts_sent` 標記，下次週期自動重試
   - 4 種報表格式化器：
     - `generate_token_summary()` — 今日摘要（成本/呼叫數/快取命中率/預算百分比）
     - `generate_token_detail()` — 30 天明細（每日成本/呼叫/模型分佈）
     - `generate_token_hourly()` — 48 小時時段分析（尖峰時段識別）
     - `generate_budget_status()` — 預算狀態（每日/每月限額與使用率）
   - `format_budget_alert()` — 預算超標告警訊息（含金額、百分比、建議動作）
3. **Telegram 控制台整合**
   - 主選單新增「💰 Token 成本」入口（2-2-2-1 排版）
   - Token 子選單 4 個頁面：📊 今日摘要、📈 30 天明細、⏰ 時段分析、💳 預算狀態
   - RBAC 權限：`view_report`（member 等級），成本資料需較高存取門檻
   - 所有 callback_data 均 < 64 bytes（最大 15 bytes）
4. **健康引擎整合**
   - 每次 health_engine 週期自動執行 Token 檢查（增量掃描 + 預算告警）
   - Dashboard 新增 Token 成本區段：今日成本、呼叫數、預算百分比（含紅黃綠燈號）
   - 錯誤處理：Dashboard Token 區塊失敗時輸出日誌（非靜默吞錯）
5. **配置治理整合**
   - `config_governance.py` 新增 `budget.daily_limit_usd`（float, 1-1000）和 `budget.monthly_limit_usd`（float, 10-10000）
   - 支援透過 Telegram 設定管理介面調整預算上限
6. **衝突分析與修復**
   - 🔴 修復：`token_tracker_state.json` 與 `usage_report_state.json` 已納入 `backup_engine.py` BACKUP_INCLUDE（防止災難恢復遺失）
   - 🔴 修復：預算告警改用回滾機制（發送失敗時移除 `alerts_sent` 標記，確保下次重試）
   - ⚠️ 修復：Dashboard Token 區塊 `except: pass` 改為 `except Exception as e: print(...)` 輸出錯誤日誌
   - ⚠️ 修復：Token 成本頁面 RBAC 從 `view_dashboard`（viewer）改為 `view_report`（member）
   - ✅ 驗證：無循環匯入、無檔案鎖定衝突、callback_data 均在限制內
   - ✅ 驗證：與現有 `usage_cost_report.py`（每日 21:00 報表）共存無衝突

**實測數據：**
- Token 掃描：300 次呼叫、8,324,517 tokens、$0.6974、10 sessions、95.2% 快取命中率
- 預算使用：每日 7.0%（$10.00 上限）、每月 0.3%（$200.00 上限）
- health_engine 即時執行：健康分數 100/A，Dashboard Token 區段正常顯示

**驗收標準（DoD）：** ✅ 全部通過
- ✅ 可追蹤每次 API 呼叫的 token 用量與成本（增量掃描，不重複計算）
- ✅ 多維度報表：今日摘要、30 天明細、時段分析、預算狀態
- ✅ 預算告警在 70%/90%/100% 門檻自動觸發，發送失敗可自動重試
- ✅ Dashboard 即時顯示 Token 成本摘要（紅黃綠燈號）
- ✅ 狀態檔已納入備份（災難恢復不遺失）
- ✅ 與現有系統無衝突（備份引擎、日誌治理、RBAC、配置治理）

### 已處理
#### 已完成的多租戶系統（基礎版）
**完成時間：** 2026-02-13
**功能概述：**
- 以 `chat_id` 為租戶主鍵的完整隔離系統
- RBAC 四層權限控制（owner > admin > member > viewer）
- 配置治理與審計日誌
- 多租戶健康引擎整合

**核心功能：**
1. **租戶管理**：租戶註冊表、目錄隔離、自動遷移
2. **權限控制**：18 項權限矩陣、高風險操作標記
3. **配置治理**：版本化配置、自動回滾、Schema 驗證
4. **審計日誌**：Append-only JSONL、操作追蹤
5. **健康引擎**：全域採集分發、租戶獨立閾值

**技術實現：**
- `tenant_manager.py` - 租戶管理
- `rbac.py` - 權限控制  
- `config_governance.py` - 配置治理
- `audit.py` - 審計日誌
- 與現有監控系統無縫整合

---

### 已處理
_（此處記錄已完成的功能需求）_

---
**最後更新時間：** 2026-02-14 15:39 (GMT+8)
**更新者：** OpenClaw

## 歷史記錄
- **2026-02-13 01:09**：建立 TodoList 檔案，設定功能需求記錄規則
- **2026-02-13 01:53**：新增「多租戶系統」功能需求
- **2026-02-13 02:01**：新增「伺服器安全防護系統」功能需求
- **2026-02-13 02:08**：新增「/monitor 指令效能優化」功能需求
- **2026-02-13 02:19**：更新「/monitor 指令效能優化」需求，增加資訊完整性分析
- **2026-02-13 02:24**：新增「API Token 使用效率優化分析」功能需求
- **2026-02-13 02:27**：新增「Telegram 主控面板系統」功能需求
- **2026-02-13 02:33**：新增「Telegram 底部固定選單功能」需求
- **2026-02-13 02:38**：新增「Telegram Inline Keyboard 主控面板系統（方案一）」詳細需求
- **2026-02-13 02:49**：新增「系統效能優化（基於 /perf 分析結果）」需求
- **2026-02-13 02:58**：新增「OpenClaw 日誌管理系統優化」需求
- **2026-02-13 03:15**：新增「/reset 後自動推送日報與監控儀表板功能」需求
- **2026-02-13 03:32**：更新「系統效能優化」需求，加入健康檢查功能
- **2026-02-13 03:32**：更新「日誌管理系統」需求，加入自動備份功能
- **2026-02-13 03:32**：更新「Telegram主控面板」需求，加入配置管理功能
- **2026-02-13 03:32**：新增「GitHub遠端備份整合系統」需求
- **2026-02-13 03:32**：新增「錯誤追蹤與報告系統」需求
- **2026-02-13 04:20**：依相似性整併為 6 大主題任務，並補充逐項實作細節與驗收標準
- **2026-02-13 15:00**：完成 Task #4 Telegram 控制台與操作體驗優化（telegram_ui.py + menu_handler.py + health_engine.py 整合，49/49 測試通過）
- **2026-02-13 22:00**：完成 Task #6 API Token 成本與效率治理（token_tracker.py + token_governance.py 新建，telegram_ui/menu_handler/health_engine/config_governance/backup_engine 整合，衝突分析 2 CRITICAL + 2 WARNING 全部修復）
- **2026-02-13 17:51**：新增「多租戶功能擴展」需求（使用者直接提出）