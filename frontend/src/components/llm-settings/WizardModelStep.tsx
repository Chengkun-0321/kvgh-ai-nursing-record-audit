"use client";

import { useState } from "react";

import { TextField } from "@/components/ui/TextField";
import { useAvailableModels } from "@/hooks/useAvailableModels";
import type { ChatgptLogin } from "@/hooks/useChatgptLogin";
import type { LlmConfigWizard } from "@/hooks/useLlmConfigWizard";
import type { LlmProvider } from "@/lib/api/llmConfigs";
import { planModelList } from "@/lib/availableModels";
import { DRAFT_FIELD_INPUT_IDS } from "@/lib/llmConfigForm";
import { getProviderOption } from "@/lib/llmProviders";

import { ModelListPicker } from "./ModelListPicker";

type WizardModelStepProps = {
  wizard: LlmConfigWizard;
};

type ModelStepProps = WizardModelStepProps & {
  login: ChatgptLogin;
};

const LOCAL_SERVER_TYPES: readonly LlmProvider[] = [
  "ollama",
  "openai_compatible",
];

const LINK_BUTTON_CLASS =
  "self-start min-h-11 rounded-lg px-1 text-body font-semibold text-accent-strong underline-offset-4 focus-ring hover:underline";

/** 手動輸入時無法偵測，本地模型需自行指定伺服器類型。 */
function LocalServerTypePicker({ wizard }: WizardModelStepProps) {
  return (
    <fieldset className="flex flex-col gap-1.5">
      <legend className="mb-1.5 text-footnote font-semibold text-ink">
        伺服器類型
      </legend>
      {LOCAL_SERVER_TYPES.map((provider) => (
        <label
          key={provider}
          className="flex min-h-11 items-center gap-2 text-body text-ink"
        >
          <input
            type="radio"
            name="local-server-type"
            checked={wizard.draft.provider === provider}
            onChange={() => wizard.updateField("provider", provider)}
            className="size-4.5 accent-accent-strong focus-ring"
          />
          {getProviderOption(provider).label}
        </label>
      ))}
    </fieldset>
  );
}

function ManualModelInput({ wizard }: WizardModelStepProps) {
  return (
    <>
      <TextField
        id={DRAFT_FIELD_INPUT_IDS.model}
        label="模型名稱"
        value={wizard.draft.model}
        onChange={(value) => wizard.updateField("model", value)}
        placeholder={`例：${getProviderOption(wizard.draft.provider).modelExample}`}
        spellCheck={false}
        autoComplete="off"
        error={wizard.errors.model}
        hint="輸入服務商的模型 ID，不需加上 openai/、gemini/ 等前綴。"
        maxLength={200}
      />
      {wizard.choice === "local" && <LocalServerTypePicker wizard={wizard} />}
    </>
  );
}

/**
 * 第 3 步：自動列出服務目前可用的模型供選擇；清單取不到或找不到想要的模型時可改為手動輸入。
 */
export function WizardModelStep({ wizard, login }: ModelStepProps) {
  const [isManual, setIsManual] = useState(false);
  const isChatgptSignedIn = login.status.state === "signed_in";
  const { state, reload } = useAvailableModels(
    planModelList(wizard.config, wizard.draft, isChatgptSignedIn),
    wizard.applyDetection,
  );

  return (
    <div className="flex flex-col gap-4">
      {isManual ? (
        <ManualModelInput wizard={wizard} />
      ) : (
        <ModelListPicker
          provider={wizard.draft.provider}
          state={state}
          value={wizard.draft.model}
          error={wizard.errors.model}
          onSelect={wizard.selectModel}
          onReload={reload}
        />
      )}
      <button
        type="button"
        onClick={() => setIsManual((previous) => !previous)}
        className={LINK_BUTTON_CLASS}
      >
        {isManual ? "改回從清單選擇" : "清單中沒有想要的模型？改為手動輸入"}
      </button>
    </div>
  );
}
