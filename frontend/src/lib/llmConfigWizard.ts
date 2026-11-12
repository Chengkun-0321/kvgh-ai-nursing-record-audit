import type { LlmConfig } from "@/lib/api/llmConfigs";
import type {
  LlmProviderCatalog,
  ProviderChoice,
} from "@/lib/api/llmProviders";
import { draftFromConfig, type LlmConfigDraft } from "@/lib/llmConfigForm";

/** 由儲存的服務類型推回畫面上的選項（對照表由後端提供）。 */
export function toProviderChoice(
  catalog: LlmProviderCatalog,
  provider: LlmConfig["provider"],
): ProviderChoice {
  const option = catalog.providers.find((item) => item.provider === provider);
  return option?.choice ?? "local";
}

function providerForChoice(
  catalog: LlmProviderCatalog,
  choice: ProviderChoice,
  config: LlmConfig | null,
): LlmConfig["provider"] {
  // 編輯中的設定就屬於這個選項時沿用其類型（例如本地模型已偵測為 OpenAI 相容）
  if (config && toProviderChoice(catalog, config.provider) === choice) {
    return config.provider;
  }
  const option = catalog.choices.find((item) => item.choice === choice);
  return option?.default_provider ?? config?.provider ?? "openai";
}

/**
 * 套用服務類型選擇（表單狀態，不涉及驗證）：回到原本的類型時還原原本的連線設定與模型，
 * 換成其他類型則清空，避免把 A 服務的模型或金鑰帶到 B 服務。名稱與逾時保留。
 */
export function applyProviderChoice(
  catalog: LlmProviderCatalog,
  draft: LlmConfigDraft,
  choice: ProviderChoice,
  config: LlmConfig | null,
): LlmConfigDraft {
  if (toProviderChoice(catalog, draft.provider) === choice) {
    return draft;
  }
  const original =
    config && toProviderChoice(catalog, config.provider) === choice
      ? draftFromConfig(config)
      : null;
  return {
    ...draft,
    provider: providerForChoice(catalog, choice, config),
    model: original?.model ?? "",
    api_base: original?.api_base ?? "",
    api_key: "",
    clear_api_key: false,
  };
}
