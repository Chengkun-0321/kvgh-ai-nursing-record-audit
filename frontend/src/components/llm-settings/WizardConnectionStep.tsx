"use client";

import { TextField } from "@/components/ui/TextField";
import type { ChatgptLogin } from "@/hooks/useChatgptLogin";
import type { LlmConfigWizard } from "@/hooks/useLlmConfigWizard";
import type { LlmProvider } from "@/lib/api/llmConfigs";
import { DRAFT_FIELD_INPUT_IDS } from "@/lib/llmConfigForm";

import { ApiKeyField } from "./ApiKeyField";
import { ChatgptLoginPanel } from "./ChatgptLoginPanel";
import { useProviderOption } from "./LlmCatalogContext";

type WizardConnectionStepProps = {
  wizard: LlmConfigWizard;
  login: ChatgptLogin;
};

// 各服務取得金鑰的位置，讓使用者知道去哪裡拿
const KEY_SOURCE_HINTS: Partial<Record<LlmProvider, string>> = {
  openai: "在 OpenAI Platform（platform.openai.com）的 API keys 頁面建立。",
  gemini: "在 Google AI Studio（aistudio.google.com）取得。",
};

function LocalServerFields({ wizard }: { wizard: LlmConfigWizard }) {
  const { draft, errors, updateField } = wizard;
  const option = useProviderOption(draft.provider);
  // 預設位址與範例由後端目錄提供
  const placeholder = option.default_api_base
    ? `留空使用 ${option.default_api_base}`
    : `例：${option.api_base_example ?? ""}`;
  return (
    <TextField
      id={DRAFT_FIELD_INPUT_IDS.api_base}
      label="伺服器位址"
      isOptional
      type="url"
      inputMode="url"
      value={draft.api_base}
      onChange={(value) => updateField("api_base", value)}
      placeholder={placeholder}
      spellCheck={false}
      autoComplete="off"
      error={errors.api_base}
      hint="Ollama 在本機時可留空；LM Studio 例：http://localhost:1234。系統會自動判斷伺服器類型。"
    />
  );
}

/** API 金鑰：雲端服務必填；本地伺服器需要驗證時才填。 */
function ConnectionKeyField({ wizard }: { wizard: LlmConfigWizard }) {
  const { draft, errors, updateField, check } = wizard;
  const option = useProviderOption(draft.provider);
  // 已儲存金鑰的遮罩值由後端判斷（換了服務類型就沒有）；勾選「移除」後仍會回傳，才能取消勾選
  const storedHint = check?.result.stored_api_key_hint ?? null;
  return (
    <ApiKeyField
      id={DRAFT_FIELD_INPUT_IDS.api_key}
      value={draft.api_key}
      onChange={(value) => updateField("api_key", value)}
      requirement={option.api_key === "required" ? "required" : "optional"}
      storedHint={storedHint}
      isClearing={draft.clear_api_key}
      onClearingChange={(value) => updateField("clear_api_key", value)}
      example={option.api_key_example ?? undefined}
      error={errors.api_key}
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
