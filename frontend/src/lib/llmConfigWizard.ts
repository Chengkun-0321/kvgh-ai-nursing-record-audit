import type { LlmConfig, LlmProvider } from "@/lib/api/llmConfigs";
import {
  draftFromConfig,
  keepsStoredApiKey,
  type LlmConfigDraft,
  type LlmConfigDraftErrors,
  type LlmConfigDraftField,
  validateDraft,
} from "@/lib/llmConfigForm";
import {
  getProviderOption,
  isLocalProvider,
  type ProviderChoice,
  toProviderChoice,
} from "@/lib/llmProviders";

export type WizardStepId = "provider" | "connection" | "model" | "details";

export type WizardStep = { id: WizardStepId; title: string };

/** 新增與編輯共用的步驟，一步一頁。 */
export const WIZARD_STEPS: readonly WizardStep[] = [
  { id: "provider", title: "選擇服務類型" },
  { id: "connection", title: "連線設定" },
  { id: "model", title: "選擇模型" },
  { id: "details", title: "命名與確認" },
];

const STEP_FIELDS: Record<WizardStepId, readonly LlmConfigDraftField[]> = {
  provider: [],
  connection: ["apiBase", "apiKey"],
  model: ["model"],
  details: ["name", "timeoutSeconds"],
};

// 與後端 LLM_CONFIG_NAME_MAX_LENGTH 一致
const NAME_MAX_LENGTH = 100;
const OLLAMA_PROVIDER: LlmProvider = "ollama";

/** 只檢查該步驟負責的欄位。 */
export function validateStep(
  stepId: WizardStepId,
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): LlmConfigDraftErrors {
  const errors = validateDraft(draft, keepsStoredApiKey(config, draft));
  return Object.fromEntries(
    STEP_FIELDS[stepId].flatMap((field) =>
      errors[field] ? [[field, errors[field]]] : [],
    ),
  );
}

function providerForChoice(
  choice: ProviderChoice,
  config: LlmConfig | null,
): LlmProvider {
  if (choice !== "local") {
    return choice;
  }
  // 本地模型先假設為 Ollama，實際類型由模型清單偵測後更新
  return config && isLocalProvider(config.provider)
    ? config.provider
    : OLLAMA_PROVIDER;
}

/**
 * 套用服務類型選擇：回到原本的類型時還原原本的連線設定與模型，換成其他類型則清空，
 * 避免把 A 服務的模型或金鑰帶到 B 服務。名稱與逾時保留。
 */
export function applyProviderChoice(
  draft: LlmConfigDraft,
  choice: ProviderChoice,
  config: LlmConfig | null,
): LlmConfigDraft {
  if (toProviderChoice(draft.provider) === choice) {
    return draft;
  }
  const original =
    config && toProviderChoice(config.provider) === choice
      ? draftFromConfig(config)
      : null;
  return {
    ...draft,
    provider: providerForChoice(choice, config),
    model: original?.model ?? "",
    apiBase: original?.apiBase ?? "",
    apiKey: "",
    clearApiKey: false,
  };
}

/** 預設名稱，例如「Codex・API 金鑰・gpt-5.3-codex」。 */
export function suggestConfigName(draft: LlmConfigDraft): string {
  const label = getProviderOption(draft.provider).label;
  return `${label}・${draft.model.trim()}`.slice(0, NAME_MAX_LENGTH);
}
