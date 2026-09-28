import {
  createLlmConfig,
  type LlmConfig,
  type LlmConfigCreate,
  type LlmConfigUpdate,
  type LlmProvider,
  updateLlmConfig,
} from "@/lib/api/llmConfigs";
import { getProviderOption } from "@/lib/llmProviders";

/** 表單欄位一律以字串保存，送出時才轉成 API 格式。 */
export type LlmConfigDraft = {
  name: string;
  provider: LlmProvider;
  model: string;
  apiBase: string;
  apiKey: string;
  timeoutSeconds: string;
  clearApiKey: boolean;
};

export type LlmConfigDraftField =
  "name" | "model" | "apiBase" | "apiKey" | "timeoutSeconds";

export type LlmConfigDraftErrors = Partial<Record<LlmConfigDraftField, string>>;

// 與 backend/app/core/constants.py 一致
export const TIMEOUT_MIN_SECONDS = 5;
export const TIMEOUT_MAX_SECONDS = 600;
// 未填逾時時後端使用的預設值（Settings.LLM_DEFAULT_TIMEOUT_SECONDS 的預設）
export const DEFAULT_TIMEOUT_SECONDS = 60;
const DEFAULT_PROVIDER: LlmProvider = "openai";
const HTTP_URL_PATTERN = /^https?:\/\/[^\s/]+/i;
// 依逐步表單的順序：連線設定 → 模型 → 命名
const DRAFT_FIELD_ORDER: readonly LlmConfigDraftField[] = [
  "apiBase",
  "apiKey",
  "model",
  "name",
  "timeoutSeconds",
];

/** 新增設定的空白表單。 */
export function createEmptyDraft(): LlmConfigDraft {
  return {
    name: "",
    provider: DEFAULT_PROVIDER,
    model: "",
    apiBase: "",
    apiKey: "",
    timeoutSeconds: "",
    clearApiKey: false,
  };
}

/** 以已儲存的設定填入表單；API 金鑰永遠留空（只顯示遮罩值）。 */
export function draftFromConfig(config: LlmConfig): LlmConfigDraft {
  return {
    name: config.name,
    provider: config.provider,
    model: config.model,
    apiBase: config.api_base ?? "",
    apiKey: "",
    timeoutSeconds: String(config.timeout_seconds),
    clearApiKey: false,
  };
}

/**
 * 表單送出後是否仍保有可用的已儲存金鑰；換了服務類型時，舊金鑰屬於另一個服務，不沿用
 * （與後端 config_service 規則一致）。
 */
export function keepsStoredApiKey(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): boolean {
  return (
    config?.has_api_key === true &&
    config.provider === draft.provider &&
    !draft.clearApiKey
  );
}

/** 是否為 http(s) 位址（送出前的基本檢查，完整驗證在後端）。 */
export function isHttpUrl(value: string): boolean {
  return HTTP_URL_PATTERN.test(value.trim());
}

function validateApiBase(draft: LlmConfigDraft): string | undefined {
  const { apiBase } = getProviderOption(draft.provider);
  const value = draft.apiBase.trim();
  if (apiBase === "unused") {
    return undefined;
  }
  if (!value) {
    return apiBase === "required" ? "請輸入 API 位址" : undefined;
  }
  return isHttpUrl(value)
    ? undefined
    : "API 位址必須以 http:// 或 https:// 開頭";
}

function validateApiKey(
  draft: LlmConfigDraft,
  hasStoredKey: boolean,
): string | undefined {
  const { apiKey } = getProviderOption(draft.provider);
  const isMissing = !draft.apiKey.trim() && !hasStoredKey;
  return apiKey === "required" && isMissing ? "請輸入 API 金鑰" : undefined;
}

function validateTimeout(value: string): string | undefined {
  if (!value.trim()) {
    return undefined;
  }
  const seconds = Number(value);
  const isValid =
    Number.isInteger(seconds) &&
    seconds >= TIMEOUT_MIN_SECONDS &&
    seconds <= TIMEOUT_MAX_SECONDS;
  return isValid
    ? undefined
    : `請輸入 ${TIMEOUT_MIN_SECONDS}–${TIMEOUT_MAX_SECONDS} 的整數`;
}

/** 檢查表單；回傳各欄位的錯誤訊息（沒有錯誤時為空物件）。 */
export function validateDraft(
  draft: LlmConfigDraft,
  hasStoredKey: boolean,
): LlmConfigDraftErrors {
  const errors: LlmConfigDraftErrors = {
    name: draft.name.trim() ? undefined : "請輸入名稱",
    model: draft.model.trim() ? undefined : "請輸入模型名稱",
    apiBase: validateApiBase(draft),
    apiKey: validateApiKey(draft, hasStoredKey),
    timeoutSeconds: validateTimeout(draft.timeoutSeconds),
  };
  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => message !== undefined),
  );
}

function toNullable(value: string): string | null {
  return value.trim() || null;
}

/** 轉成新增設定的 API 格式；該服務類型用不到的欄位不送出。 */
export function toCreatePayload(draft: LlmConfigDraft): LlmConfigCreate {
  const option = getProviderOption(draft.provider);
  return {
    name: draft.name.trim(),
    provider: draft.provider,
    model: draft.model.trim(),
    api_base: option.apiBase === "unused" ? null : toNullable(draft.apiBase),
    api_key: option.apiKey === "unused" ? null : toNullable(draft.apiKey),
    timeout_seconds: draft.timeoutSeconds.trim()
      ? Number(draft.timeoutSeconds)
      : null,
  };
}

/** 轉成更新設定的 API 格式；API 金鑰留空表示沿用已儲存的金鑰。 */
export function toUpdatePayload(draft: LlmConfigDraft): LlmConfigUpdate {
  return { ...toCreatePayload(draft), clear_api_key: draft.clearApiKey };
}

/** 儲存表單：`config` 為 `null` 時新增，否則更新該設定。 */
export function saveLlmConfigDraft(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): Promise<LlmConfig> {
  return config
    ? updateLlmConfig(config.id, toUpdatePayload(draft))
    : createLlmConfig(toCreatePayload(draft));
}

/** 各欄位輸入框的 id；檢查失敗時用來把焦點移到第一個錯誤欄位。 */
export const DRAFT_FIELD_INPUT_IDS: Record<LlmConfigDraftField, string> = {
  name: "llm-config-name",
  model: "llm-config-model",
  apiBase: "llm-config-api-base",
  apiKey: "llm-config-api-key",
  timeoutSeconds: "llm-config-timeout",
};

/** 表單中第一個有錯誤的欄位（依畫面順序），用於送出失敗時移動焦點。 */
export function getFirstErrorField(
  errors: LlmConfigDraftErrors,
): LlmConfigDraftField | undefined {
  return DRAFT_FIELD_ORDER.find((field) => errors[field] !== undefined);
}
