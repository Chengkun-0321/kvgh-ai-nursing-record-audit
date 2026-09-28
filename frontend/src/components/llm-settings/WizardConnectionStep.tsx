"use client";

import { TextField } from "@/components/ui/TextField";
import type { ChatgptLogin } from "@/hooks/useChatgptLogin";
import type { LlmConfigWizard } from "@/hooks/useLlmConfigWizard";
import { DRAFT_FIELD_INPUT_IDS, keepsStoredApiKey } from "@/lib/llmConfigForm";
import { getProviderOption } from "@/lib/llmProviders";

import { ApiKeyField } from "./ApiKeyField";
import { ChatgptLoginPanel } from "./ChatgptLoginPanel";

type WizardConnectionStepProps = {
  wizard: LlmConfigWizard;
  login: ChatgptLogin;
};

// 各服務取得金鑰的位置，讓使用者知道去哪裡拿
const KEY_SOURCE_HINTS: Partial<Record<string, string>> = {
  openai: "在 OpenAI Platform（platform.openai.com）的 API keys 頁面建立。",
  gemini: "在 Google AI Studio（aistudio.google.com）取得。",
};

function LocalServerFields({ wizard }: { wizard: LlmConfigWizard }) {
  const { draft, errors, updateField } = wizard;
  return (
    <TextField
      id={DRAFT_FIELD_INPUT_IDS.apiBase}
      label="伺服器位址"
      isOptional
      type="url"
      inputMode="url"
      value={draft.apiBase}
      onChange={(value) => updateField("apiBase", value)}
      placeholder="留空使用 http://localhost:11434"
      spellCheck={false}
      autoComplete="off"
      error={errors.apiBase}
      hint="Ollama 在本機時可留空；LM Studio 例：http://localhost:1234。系統會自動判斷伺服器類型。"
    />
  );
}

/** API 金鑰：雲端服務必填；本地伺服器需要驗證時才填。 */
function ConnectionKeyField({ wizard }: { wizard: LlmConfigWizard }) {
  const { config, draft, errors, updateField, choice } = wizard;
  const storedHint = keepsStoredApiKey(config, draft)
    ? (config?.api_key_hint ?? null)
    : null;
  return (
    <ApiKeyField
      id={DRAFT_FIELD_INPUT_IDS.apiKey}
      value={draft.apiKey}
      onChange={(value) => updateField("apiKey", value)}
      requirement={choice === "local" ? "optional" : "required"}
      storedHint={storedHint}
      isClearing={draft.clearApiKey}
      onClearingChange={(value) => updateField("clearApiKey", value)}
      example={getProviderOption(draft.provider).apiKeyExample}
      error={errors.apiKey}
      sourceHint={KEY_SOURCE_HINTS[draft.provider]}
    />
  );
}

/** 第 2 步：依服務類型只顯示需要的連線欄位。 */
export function WizardConnectionStep({
  wizard,
  login,
}: WizardConnectionStepProps) {
  if (wizard.choice === "chatgpt") {
    return (
      <div className="flex flex-col gap-3">
        <ChatgptLoginPanel login={login} />
        <p className="text-footnote text-ink-secondary">
          尚未登入也可以先完成設定；使用前（包含測試對話）需要登入。
        </p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-5">
      {wizard.choice === "local" && <LocalServerFields wizard={wizard} />}
      <ConnectionKeyField wizard={wizard} />
    </div>
  );
}
