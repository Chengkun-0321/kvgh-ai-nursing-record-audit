"use client";

import { TextField } from "@/components/ui/TextField";
import type { LlmConfigWizard } from "@/hooks/useLlmConfigWizard";
import {
  DEFAULT_TIMEOUT_SECONDS,
  DRAFT_FIELD_INPUT_IDS,
  TIMEOUT_MAX_SECONDS,
  TIMEOUT_MIN_SECONDS,
} from "@/lib/llmConfigForm";
import { describeDraft } from "@/lib/llmConfigSummary";

import { SummaryList } from "./SummaryList";

type WizardDetailsStepProps = {
  wizard: LlmConfigWizard;
};

/** 第 4 步：命名、逾時與確認摘要；按下「新增設定」／「儲存變更」才寫入後端。 */
export function WizardDetailsStep({ wizard }: WizardDetailsStepProps) {
  const { draft, errors, updateField } = wizard;
  return (
    <div className="flex flex-col gap-5">
      <TextField
        id={DRAFT_FIELD_INPUT_IDS.name}
        label="名稱"
        value={draft.name}
        onChange={(value) => updateField("name", value)}
        placeholder="例：Codex 正式、本機 Ollama"
        error={errors.name}
        hint="用來在清單中辨識這組設定，不可與其他設定重複。"
        maxLength={100}
      />
      <TextField
        id={DRAFT_FIELD_INPUT_IDS.timeoutSeconds}
        label="逾時（秒）"
        isOptional
        inputMode="numeric"
        value={draft.timeoutSeconds}
        onChange={(value) => updateField("timeoutSeconds", value)}
        placeholder={String(DEFAULT_TIMEOUT_SECONDS)}
        error={errors.timeoutSeconds}
        hint={`${TIMEOUT_MIN_SECONDS}–${TIMEOUT_MAX_SECONDS} 秒，超過即視為失敗；本地模型較慢時可調高。`}
      />
      <section
        aria-labelledby="wizard-summary-heading"
        className="flex flex-col gap-2"
      >
        <h3 id="wizard-summary-heading" className="text-headline">
          確認設定
        </h3>
        <SummaryList rows={describeDraft(wizard.config, draft)} />
      </section>
    </div>
  );
}
