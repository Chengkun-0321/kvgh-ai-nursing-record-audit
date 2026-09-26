# LLM 使用規範（LiteLLM）

## 唯一出口

- 所有 LLM 呼叫只經 `app/services/llm/gateway.py`
- 禁止在其他地方 import `litellm`、`openai`、`anthropic` 等 SDK
- 模型名稱使用 LiteLLM 格式 `provider/model`（如 `openai/…`、`anthropic/…`、`ollama/…`），不寫死在程式，由使用者設定

## 模型設定（網頁）

- 欄位：名稱、provider/model、`api_base`（選填）、API key、timeout、是否啟用
- 同一時間只有一組啟用中的設定；gateway 每次呼叫讀取啟用中的設定
- 提供「測試連線」API：以固定短 prompt 驗證設定可用
- 設定變更寫入 `setting_change_logs`（不含 key 值）

## API key 安全

- 以 Fernet（`cryptography`）加密存 DB，加密金鑰來自環境變數 `LLM_KEY_ENCRYPTION_KEY`
- 只在 gateway 呼叫當下解密，不存入任何全域變數或快取
- API 回傳前端只給遮罩值（如 `sk-…abcd`），前端永遠拿不到明文
- 不得出現在 log、例外訊息、稽核結果中；不開啟 LiteLLM 的 verbose／debug log

## gateway 介面

```python
async def complete_structured(
    request: LLMRequest,           # rule_code、prompt 名稱與版本、模板變數
    output_schema: type[T],        # 期望輸出的 Pydantic model
) -> LLMResult[T]:                 # parsed、model、prompt_version、token 用量、成本、耗時
```

執行步驟：

1. 讀取啟用中的模型設定並解密 key
2. 以 `prompt_loader` 渲染 prompt
3. `preprocess` hook（目前 pass-through；未來接真實資料時插入去識別化，見 [ADR 0002](../adr/0002-llm-phi-policy.md)）
4. `litellm.acompletion(...)`：`temperature=0`、`timeout` 取自設定；模型支援時使用 `response_format` 要求 JSON
5. 以 `output_schema` 驗證輸出；失敗時附上驗證錯誤重試，最多 `LLM_MAX_RETRIES` 次
6. 仍失敗 → 拋出 `LLMOutputError`，規則轉為 `NEEDS_REVIEW`，**絕不靜默視為 PASS**
7. 記錄 model、prompt_version、token 用量、成本（`litellm.completion_cost`）、耗時

網路錯誤、429、timeout 以指數退避重試（LiteLLM `num_retries`），與第 5 步的格式重試分開計算。

## Prompt 規範

- 位置：`app/prompts/<rule_code>_<name>/v<N>.j2`（Jinja2），內容繁中
- 版本：已用於產出稽核結果的 prompt 不得就地修改語意，改版請新增 `v<N+1>.j2`；稽核結果記錄 `prompt_version`，確保可重現
- 必要要素清單由程式常數注入，不在 prompt 內重複寫死
- 結構：

```
[角色] 你是護理紀錄稽核助理，只做紀錄一致性與完整性檢查，不做臨床判斷。
[任務] 本規則要檢查什麼。
[判斷準則] 必要要素（由程式注入）、何種情況屬於不一致。
[輸入資料] 每筆資料以標籤標示來源與 record_id，例：
  <record source="nursing_progress_note" id="…" date="…">…</record>
[輸出格式] JSON，符合 output_schema。
[限制]
  - 只根據提供的資料判斷，不得推測或補完
  - 每個結論必須引用原文片段（excerpt）與 record_id
  - 資料不足以判斷時回傳 NEEDS_REVIEW
```

## Hallucination guard

- LLM 回傳的每筆 Evidence，後端須驗證 `excerpt` 確實存在於對應 `record_id` 的原文（正規化空白後比對）
- 驗證失敗的 Evidence 丟棄；若無任何有效 Evidence，結果降為 `NEEDS_REVIEW`

## 測試與評估

- 單元測試一律 mock gateway，不打真實 API
- 準確率評估與單元測試分開：`backend/evaluation/` 以護理長標註的 golden set 計算各規則 precision／recall／F1，手動執行（會產生費用）
