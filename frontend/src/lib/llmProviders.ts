import type { LlmProvider } from "@/lib/api/llmConfigs";

/** 設定欄位在該服務類型是否需要；規則與 backend/app/services/llm/providers.py 一致。 */
export type FieldRequirement = "required" | "optional" | "unused";

export type LlmProviderOption = {
  value: LlmProvider;
  label: string;
  description: string;
  apiKey: FieldRequirement;
  apiBase: FieldRequirement;
  /** 未填 API 位址時後端使用的預設值（顯示為提示） */
  defaultApiBase?: string;
  apiBaseExample?: string;
  apiKeyExample?: string;
  modelExample: string;
};

// 以 Record 定義，新增服務類型時型別檢查會要求補齊
const PROVIDER_OPTIONS: Record<LlmProvider, LlmProviderOption> = {
  openai: {
    value: "openai",
    label: "Codex・API 金鑰",
    description: "使用 OpenAI Platform 的 API 金鑰，依用量計費",
    apiKey: "required",
    apiBase: "unused",
    apiKeyExample: "sk-…",
    modelExample: "gpt-5.3-codex",
  },
  chatgpt: {
    value: "chatgpt",
    label: "Codex・ChatGPT 訂閱",
    description: "以 ChatGPT Plus／Pro 帳號登入，不需要 API 金鑰",
    apiKey: "unused",
    apiBase: "unused",
    modelExample: "gpt-5.3-codex",
  },
  gemini: {
    value: "gemini",
    label: "Gemini",
    description: "使用 Google AI Studio 的 API 金鑰",
    apiKey: "required",
    apiBase: "unused",
    apiKeyExample: "AIza…",
    modelExample: "gemini-3.5-flash",
  },
  ollama: {
    value: "ollama",
    label: "本地模型（Ollama）",
    description: "連線到本機或院內的 Ollama 伺服器",
    apiKey: "unused",
    apiBase: "optional",
    defaultApiBase: "http://localhost:11434",
    modelExample: "llama3.2",
  },
  openai_compatible: {
    value: "openai_compatible",
    label: "本地模型（OpenAI 相容）",
    description: "LM Studio、vLLM、llama.cpp 等提供 /v1 介面的伺服器",
    apiKey: "optional",
    apiBase: "required",
    apiBaseExample: "http://localhost:1234/v1",
    modelExample: "qwen3-8b",
  },
};

/**
 * 使用者選擇的服務類型：Ollama 與 OpenAI 相容伺服器合併為「本地模型」，
 * 由後端依伺服器位址自動判斷實際類型（儲存時仍為 `ollama`／`openai_compatible`）。
 */
export type ProviderChoice = "openai" | "chatgpt" | "gemini" | "local";

export type ProviderChoiceOption = {
  value: ProviderChoice;
  label: string;
  description: string;
};

function toChoiceOption(
  value: Exclude<ProviderChoice, "local">,
): ProviderChoiceOption {
  const { label, description } = PROVIDER_OPTIONS[value];
  return { value, label, description };
}

/** 第 1 步的選項順序：Codex、Gemini、本地模型。 */
export const PROVIDER_CHOICES: readonly ProviderChoiceOption[] = [
  toChoiceOption("openai"),
  toChoiceOption("chatgpt"),
  toChoiceOption("gemini"),
  {
    value: "local",
    label: "本地模型",
    description:
      "Ollama、LM Studio、vLLM 等本機或院內伺服器；系統自動判斷伺服器類型",
  },
];

/** 是否為「本地模型」涵蓋的伺服器類型。 */
export function isLocalProvider(provider: LlmProvider): boolean {
  return provider === "ollama" || provider === "openai_compatible";
}

/** 由儲存的服務類型推回畫面上的選項。 */
export function toProviderChoice(provider: LlmProvider): ProviderChoice {
  return provider === "ollama" || provider === "openai_compatible"
    ? "local"
    : provider;
}

/** 取得服務類型的顯示名稱與欄位規則。 */
export function getProviderOption(provider: LlmProvider): LlmProviderOption {
  return PROVIDER_OPTIONS[provider];
}
