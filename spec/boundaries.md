# ② 系統邊界

## 範圍
- 範圍內：
  - 院內格式 v0.1.0 每日資料包的匯入：整份驗證，只正規化 R02 需要的區塊
  - 稽核項目 R02 的手動觸發稽核與結果保存，包含三部分：複製／一成不變、相似但臨床資料已變化、引用非當日資料
  - 兩支 API
  - 病患頁的每日稽核清單
  - 護理紀錄頁連到病患頁的連結
- 範圍外（明確不做）：
  - 自動排程
  - 其他稽核項目（R01、R03～R11）
  - 首頁病床總覽改接真實資料
  - 登入與權限
  - 中繼站（`RelaySource`）
  - R02 以外區塊的正規化：入院評估、每日身評、轉入轉出、會診、藥囑、選填區塊只驗證並保留原始檔
  - 用程式計算文字相似度、設定相似度門檻
  - 修改或回寫任何院內資料
  - Alembic migration（由人產生）

## 邊界條目

| 編號 | 邊界 | 驗證方式 |
|---|---|---|
| B1 | `GET /api/v1/patients/{patient_key}/audit-days` → 200：`{"patient_key": str, "days": [{"business_date": "YYYY-MM-DD", "admission_id": str, "auditable": bool, "not_auditable_reason": str \| null, "latest_finding": AuditFinding \| null}]}`，`days` 依日期由新到舊。 | 測試 |
| B2 | `POST /api/v1/audit-runs`，body `{"patient_key": str, "business_date": "YYYY-MM-DD", "rule_code": "R02"}`（`rule_code` 可省略，預設 `"R02"`）→ 201，回傳 `AuditFinding`。欄位：<br>• `id`、`audit_run_id`、`rule_code`、`patient_key`、`business_date`<br>• `verdict`：`"PASS"` \| `"WARNING"` \| `"NEEDS_REVIEW"`<br>• `message`：str<br>• `evidence`：`[{"source", "record_id", "field", "recorded_at", "excerpt"}]`<br>• `note_similarities`：`[{"record_id", "recorded_at", "similar_record_id": str \| null, "similar_business_date": "YYYY-MM-DD" \| null, "similarity_percent": number \| null, "issue_types": ["copy" \| "unchanged" \| "clinical_changed" \| "outdated_reference"]}]`<br>• `engine`：`"llm"`<br>• `model`：str \| null<br>• `prompt_version`：str \| null<br>• `system_prompt_version`：int \| null<br>• `audited_at`：datetime | 測試 |
| B3 | 院內資料只讀：`LocalFixtureSource` 不寫入 `MOCK_DATA_DIR`；匯入時把原始檔原封複製到 `RAW_DATA_DIR/<YYYY-MM-DD>/`，內容的 sha256 與來源相同。 | 測試 |
| B4 | 信任邊界：`patient_key`（1～64 字元）、`business_date`（ISO 日期）、`rule_code`（只接受 `"R02"`）在 API 層以 Pydantic 驗證；資料檔內容在 `schemas/ingestion/` 驗證；service 與規則假設輸入合法。 | 審查 |
| B5 | `gateway.complete_structured(request, output_schema)` 的行為：<br>• 讀取使用中的模型設定<br>• 訊息依序為共用 system prompt（非空時）、規則 prompt<br>• `temperature=0`<br>• 以 `output_schema` 驗證輸出；失敗時附上驗證錯誤重試，最多 `LLM_MAX_RETRIES` 次，仍失敗就拋出 `LLMOutputError`<br>• 回傳 `parsed`、`model`、`prompt_version`、`system_prompt_version`<br>既有的測試對話（`/llm-configs/{id}/chat`）行為不變。 | 測試 |
| B6 | 測試不發出網路請求：LLM 以假的 `StructuredLLM` 或 mock 的 `litellm.acompletion` 取代；資料目錄與原始檔目錄都用 `tmp_path`。 | 審查 |
| B7 | 前端：Server Component 經 `API_BASE_URL` 取得 `audit-days`；瀏覽器端的 `runAudit` 呼叫同網域的 `/api/v1/audit-runs`；錯誤一律轉成 `ApiError`。 | 審查 |
| B8 | API 錯誤回應的 `detail` 為繁中，不含紀錄內文；log 只記 `patient_key`、`record_id`、規則代碼、批次 ID。 | 測試（錯誤回應內容）＋審查（log） |
