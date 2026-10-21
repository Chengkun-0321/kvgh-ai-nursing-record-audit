# ③ 業務規則與異常行為

使用者在病患頁點某一天的「執行稽核」，系統匯入資料，比對當日與前 2 個有資料業務日的護理過程紀錄，由 LLM 判斷是否有複製／一成不變／引用非當日資料，結果存入 DB 並顯示在病患頁（稽核項目 R02）。

| 編號 | 規則 | 稽核項目 |
|---|---|---|
| BR1 | `audit-days` 列出該 `patient_key` 出現在各業務日 `manifest.json` 的所有日期，由新到舊排列。<br>某日期在同一 `admission_id` 中沒有更早的資料日 → `auditable=false`，`not_auditable_reason="入院首日，無前日紀錄可比較"`；其餘日期 `auditable=true`，原因為 `null`。<br>例：B 病患有 9/01～9/10 的資料 → 9/01 不可稽核，9/02～9/10 可稽核。 | R02 |
| BR2 | 比對範圍＝當日＋同一 `admission_id` 中早於當日、該病患有資料包的最近 2 個業務日（`R02_LOOKBACK_DAYS`）。沒有資料的日期直接跳過。<br>例：A 病患 9/17 → 比對 9/17、9/14、9/13；B 病患 9/02 → 比對 9/02、9/01。 | R02 |
| BR3 | 執行稽核時，比對範圍內每個日期的資料包若尚未匯入（`ingestion_batches` 沒有相同 sha256 的紀錄），就先匯入再稽核；已匯入的不重複匯入。 | - |
| BR4 | 匯入步驟：<br>1. 原始檔原封複製到 `RAW_DATA_DIR/<YYYY-MM-DD>/`<br>2. 寫一筆 `ingestion_batches`（來源、業務日期、檔名、sha256、狀態、成功／失敗／略過筆數）<br>3. 整份病患檔依 v0.1.0 驗證<br>4. 病患／住院、護理過程紀錄、生命徵象、檢驗、管路依 record_id 新增，已存在就以新內容覆蓋<br>同一份檔案重複匯入時，各資料表筆數不變。 | - |
| BR5 | 送給 LLM 的資料：比對範圍內各日的護理過程紀錄（record_id、recorded_at、title_category、title、content）、生命徵象、檢驗、管路。<br>每筆以 `<record source="…" id="…" date="…">` 標示；當日紀錄與前日紀錄分開標示。<br>必要要素（相似比對、臨床資料是否變化、引用資料日期是否為當日）由程式常數注入 prompt。 | R02 |
| BR6 | 當日每筆護理過程紀錄都有一筆 `note_similarities`：<br>• `similar_record_id`、`similarity_percent`（0～100）取自 LLM<br>• `similar_business_date` 由程式依 `similar_record_id` 查出，不採用 LLM 回傳的日期<br>• `similarity_percent` 以四捨五入（ROUND_HALF_UP）取到小數 1 位，例：97.65 → 97.7、97.64 → 97.6<br>• LLM 認為沒有相似紀錄時，`similar_record_id`、`similar_business_date`、`similarity_percent` 都是 `null` | R02 |
| BR7 | LLM 回傳 `PASS` 或 `WARNING`。<br>`WARNING` 經 BR8 驗證後至少要剩 1 筆 Evidence 才成立，否則改為 `NEEDS_REVIEW`；`PASS` 可以沒有 Evidence。<br>不產生 `ERROR`。`engine` 一律為 `"llm"`。 | R02 |
| BR8 | Evidence 驗證：<br>• Evidence 的 `record_id` 必須在 BR5 送出的資料中<br>• `excerpt` 去除所有空白後，必須是該紀錄原文（同樣去除空白）的子字串<br>不符合的 Evidence 丟棄。`note_similarities` 中 `record_id` 或 `similar_record_id` 不在資料中的項目也丟棄。 | R02 |
| BR9 | `message` 依 `issue_types` 套固定模板；多種問題以「；」串接，結尾加「，請確認」：<br>• `copy`／`unchanged`：「今日 {HH:MM} 紀錄（{record_id}）與 {M/D} 紀錄（{similar_record_id}）相似 {x}%」<br>• `clinical_changed`：在前段後面加「，但生命徵象／檢驗／管路已有變化，請確認是否需更新」<br>• `outdated_reference`：「今日 {HH:MM} 紀錄（{record_id}）引用 {M/D} 的資料作為今日狀況」<br>• `PASS`：「未見與前日紀錄複製或引用非當日資料的情形」<br>訊息不得包含 audit-rules.md 的禁止用語（寫錯、抄襲、違規、沒有寫）。 | R02 |
| BR10 | 每次 `POST /audit-runs` 都新增一筆 `audit_runs`（規則代碼、業務日期、模型、開始與結束時間）和一筆 `audit_findings`；`audit-days` 的 `latest_finding` 是該日期最新的一筆。 | R02 |
| BR11 | 結果記錄 `model`、`prompt_version="r02_copy_paste/v1"`、`system_prompt_version`（取自 gateway 回傳值）、`audited_at`。 | R02 |
| BR12 | 病患頁 `/patients/[patientKey]`：每個日期一張卡，由新到舊排列。<br>卡片顯示：日期（M/D）、判定（顏色＋icon＋文字，沿用既有 verdict 樣式）、`message`、每筆 `note_similarities` 經 `formatSimilarity` 產生的文字、Evidence（來源、record_id、原文片段）、稽核時間、模型名稱。<br>未稽核的日期顯示「尚未稽核」。 | R02 |
| BR13 | 卡片按鈕：<br>• `auditable=false` → 不顯示按鈕，顯示 `not_auditable_reason`<br>• 可稽核、沒有結果 →「執行稽核」<br>• 已有結果 →「重新稽核」<br>• 請求進行中 → 按鈕停用，文字為「稽核中…」<br>成功後該卡以回傳結果更新，不重新整理頁面。 | R02 |
| BR14 | 護理紀錄頁選定病患後，顯示「查看稽核結果」連結，指向 `/patients/{patient_id}`（`patient_key` 即 `patient_id`，經 URL 編碼）。 | - |
| E1 | `patient_key` 沒有出現在任何 manifest → 404，`detail`「找不到此病患的資料」。 | |
| E2 | `business_date` 不是該病患有資料的日期 → 404，`detail`「此日期沒有該病患的資料」。 | |
| E3 | `business_date` 不是合法 ISO 日期、`patient_key` 為空或超過 64 字元、`rule_code` 不是 `"R02"` → 422。 | |
| E4 | 對 `auditable=false` 的日期執行稽核 → 422，`detail`「入院首日無前日紀錄可比較」；不寫入 `audit_runs`／`audit_findings`。 | R02 |
| E5 | 沒有使用中的模型設定 → 409，`detail`「尚未設定使用中的模型，請至設定頁設定」；不寫入 `audit_findings`。 | |
| E6 | 不呼叫 LLM，判定為 `NEEDS_REVIEW`，結果仍寫入：<br>• 當日沒有任何護理過程紀錄 → 訊息「今日未見護理過程紀錄，無法比對，請確認」<br>• 前 2 個資料日都沒有護理過程紀錄 → 訊息「前日未見護理過程紀錄，無法比對，請確認」 | R02 |
| E7 | gateway 拋出 `LLMOutputError`、逾時或連線錯誤 → `NEEDS_REVIEW`，訊息「系統無法完成判定，請稍後重試或人工確認」，`note_similarities` 為空；結果仍寫入；絕不當作 `PASS`。 | R02 |
| E8 | LLM 回傳的 `similarity_percent` 不在 0～100、`verdict` 不是 `PASS`／`WARNING`，或缺少必要欄位 → 視為輸出不符 schema，由 gateway 重試；仍失敗就依 E7 處理。 | R02 |
| E9 | 比對範圍內任一日的該病患檔驗證失敗：<br>• 寫入 `ingestion_errors`（批次 ID、檔名、JSON path、錯誤訊息，不含紀錄內文）<br>• 該次稽核為 `NEEDS_REVIEW`，訊息「{M/D} 資料格式不符，無法判定，請確認」<br>• 同批其他病患檔照常匯入 | R02 |
| E10 | 某日 `manifest.json` 不存在或無法解析 → 該日期不出現在 `audit-days`，也不納入比對範圍；log 只記日期。 | |
| E11 | 資料夾名稱不是 8 位數字 → 忽略該資料夾。manifest 的 `file` 解析後的路徑不在 `MOCK_DATA_DIR` 內 → 拒絕讀取該檔案，視為 E9 的驗證失敗。 | |
| E12 | 前端 `runAudit` 失敗 → 該卡以 `role="alert"` 顯示 `ApiError` 的繁中訊息，保留原本的結果，按鈕恢復可點。 | |
| E13 | `getAuditDays` 失敗 → 頁面顯示「無法載入稽核結果」與重試方式，不顯示任何卡片。 | |

## 決策紀錄
- 稽核項目為 R02，包含三部分：複製／一成不變、相似但臨床資料已變化、引用非當日資料（第 1 輪 2.C）。
- 比對範圍為當日＋前 2 個有資料的業務日，依 audit-rules.md 的 R02 定義（第 2 輪 1.A）。
- 判定交給 LLM，不設程式門檻（第 1 輪 3.B）。相似度 x% 也由 LLM 估計（第 4 輪 1.B）；風險是數字無法重現、也無法驗證，所以畫面上標示「模型估計」。
- 逐筆比對：今日每筆紀錄各自找前 2 個資料日中最相似的一筆（第 4 輪 2.A）。
- 判定由 LLM 給出 PASS 或 WARNING，x% 只用來顯示（第 4 輪 3.A）。分級沿用暫定 Verdict（PASS／WARNING／NEEDS_REVIEW，不產生 ERROR）。
- x% 四捨五入到小數 1 位（第 4 輪 4.B）。
- 院內 JSON 格式以 hospital-data-spec v0.1.0 為準，`mock_data/` 視為院內資料（第 2 輪）。
- 要做匯入：整份驗證，只正規化 R02 需要的區塊（第 1 輪 4.B、第 2 輪 3.A）。
- 點稽核時自動匯入；日期清單讀 manifest（第 2 輪 4.A）。
- 重複點擊時新增一筆，畫面顯示最新一筆（第 1 輪 4，重複點擊選 A）。
- 病患頁以 `patient_id` 當 patientKey，從護理紀錄頁進入；首頁不改（第 1 輪 5.A）。
- 流程紀錄存在 `flow-records/<日期時間>/`，不進版控（第 2 輪 5.A）。

## 假設
- `patient_key` 暫時等於院方的 `patient_id`（例：`A病患`）；日後改成內部代碼時再調整。
- 只比對同一次住院（同一 `admission_id`）的紀錄。
- 當日或前日沒有護理過程紀錄、未設定模型時的行為，依 E5、E6。
- 卡片顯示的內容依 BR12；相似度文字加註「（模型估計）」。
- 前端暫時把 API 型別手寫在 `src/types/patientAudit.ts`，因為流程角色無法啟動後端執行 `gen:api`；收尾時改用 `gen:api` 產生的型別取代。這暫時違反 frontend/CLAUDE.md「禁止手寫重複的 API 型別」，比照 ADR 0010 的前例處理。
- 稽核 API 為同步請求：等 LLM 完成才回應，逾時時間取模型設定的 timeout。
