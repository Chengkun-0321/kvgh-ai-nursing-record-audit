import type { LlmConfig } from "@/lib/api/llmConfigs";
import {
  DEFAULT_TIMEOUT_SECONDS,
  keepsStoredApiKey,
  type LlmConfigDraft,
} from "@/lib/llmConfigForm";
import { getProviderOption } from "@/lib/llmProviders";

export type SummaryRow = { label: string; value: string };

const NOT_REQUIRED = "不需要";
const NOT_SET = "未設定";

function describeApiBase(
  provider: LlmConfig["provider"],
  apiBase: string,
): SummaryRow | null {
  const option = getProviderOption(provider);
  if (option.apiBase === "unused") {
    return null;
  }
  const value = apiBase || `${option.defaultApiBase ?? NOT_SET}（預設）`;
  return { label: "伺服器位址", value };
}

function describeDraftKey(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): string {
  if (getProviderOption(draft.provider).apiKey === "unused") {
    return NOT_REQUIRED;
  }
  if (draft.apiKey.trim()) {
    return "已輸入新的金鑰";
  }
  return keepsStoredApiKey(config, draft)
    ? `沿用已儲存的金鑰（${config?.api_key_hint ?? ""}）`
    : NOT_SET;
}

function describeTimeout(timeoutSeconds: string): string {
  return timeoutSeconds.trim()
    ? `${timeoutSeconds.trim()} 秒`
    : `預設 ${DEFAULT_TIMEOUT_SECONDS} 秒`;
}

/** 逐步表單最後一步的確認摘要。 */
export function describeDraft(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): SummaryRow[] {
  const apiBase = describeApiBase(draft.provider, draft.apiBase.trim());
  return [
    { label: "服務類型", value: getProviderOption(draft.provider).label },
    ...(apiBase ? [apiBase] : []),
    { label: "API 金鑰", value: describeDraftKey(config, draft) },
    { label: "模型", value: draft.model.trim() || NOT_SET },
    { label: "逾時", value: describeTimeout(draft.timeoutSeconds) },
  ];
}

/** 已儲存設定的摘要（設定頁左欄）。 */
export function describeConfig(config: LlmConfig): SummaryRow[] {
  const apiBase = describeApiBase(config.provider, config.api_base ?? "");
  const usesKey = getProviderOption(config.provider).apiKey !== "unused";
  const apiKey = usesKey ? (config.api_key_hint ?? NOT_SET) : NOT_REQUIRED;
  return [
    { label: "服務類型", value: getProviderOption(config.provider).label },
    ...(apiBase ? [apiBase] : []),
    { label: "API 金鑰", value: apiKey },
    { label: "模型", value: config.model },
    { label: "逾時", value: `${config.timeout_seconds} 秒` },
  ];
}
