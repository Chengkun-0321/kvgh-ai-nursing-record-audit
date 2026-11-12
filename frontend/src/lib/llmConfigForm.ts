import {
  createLlmConfig,
  type LlmConfig,
  type LlmConfigCreate,
  type LlmProvider,
  updateLlmConfig,
} from "@/lib/api/llmConfigs";
import type { DraftField, LlmConfigDraftCheck } from "@/lib/api/llmProviders";

/**
 * 表單內容，欄位名稱與後端檢查 API 相同；一律以字串保存，格式錯誤由後端逐欄回報。
 */
export type LlmConfigDraft = Required<
  Omit<LlmConfigDraftCheck, "config_id" | "step_id">
>;

export type LlmConfigDraftErrors = Partial<Record<DraftField, string>>;

const DEFAULT_PROVIDER: LlmProvider = "openai";

/** 新增設定的空白表單。 */
export function createEmptyDraft(): LlmConfigDraft {
  return {
    name: "",
    provider: DEFAULT_PROVIDER,
    model: "",
    api_base: "",
    api_key: "",
    timeout_seconds: "",
    clear_api_key: false,
  };
}

/** 以已儲存的設定填入表單；API 金鑰永遠留空（只顯示遮罩值）。 */
export function draftFromConfig(config: LlmConfig): LlmConfigDraft {
  return {
    name: config.name,
    provider: config.provider,
    model: config.model,
    api_base: config.api_base ?? "",
    api_key: "",
    timeout_seconds: String(config.timeout_seconds),
    clear_api_key: false,
  };
}

/** 送給檢查 API 的內容。 */
export function toDraftCheck(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
  stepId: LlmConfigDraftCheck["step_id"] = null,
): LlmConfigDraftCheck {
  return { ...draft, config_id: config?.id ?? null, step_id: stepId };
}

function toCreatePayload(draft: LlmConfigDraft): LlmConfigCreate {
  // 該服務類型用不到的欄位由後端清掉；空字串由後端視為未填
  return {
    name: draft.name,
    provider: draft.provider,
    model: draft.model,
    api_base: draft.api_base || null,
    api_key: draft.api_key || null,
    timeout_seconds: draft.timeout_seconds.trim()
      ? Number(draft.timeout_seconds)
      : null,
  };
}

/** 儲存表單（送出前已經過後端檢查）：`config` 為 `null` 時新增，否則更新該設定。 */
export function saveLlmConfigDraft(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): Promise<LlmConfig> {
  const payload = toCreatePayload(draft);
  return config
    ? updateLlmConfig(config.id, {
        ...payload,
        clear_api_key: draft.clear_api_key,
      })
    : createLlmConfig(payload);
}

/** 各欄位輸入框的 id；檢查失敗時用來把焦點移到第一個錯誤欄位。 */
export const DRAFT_FIELD_INPUT_IDS: Record<DraftField, string> = {
  name: "llm-config-name",
  model: "llm-config-model",
  api_base: "llm-config-api-base",
  api_key: "llm-config-api-key",
  timeout_seconds: "llm-config-timeout",
};
