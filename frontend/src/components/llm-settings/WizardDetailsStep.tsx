"use client";

import { TextField } from "@/components/ui/TextField";
import type { LlmConfigWizard } from "@/hooks/useLlmConfigWizard";
import { DRAFT_FIELD_INPUT_IDS } from "@/lib/llmConfigForm";

import { useLlmCatalog } from "./LlmCatalogContext";
import { SummaryList } from "./SummaryList";

type WizardDetailsStepProps = {
  wizard: LlmConfigWizard;
};

/** 第 4 步：命名、逾時與確認摘要；按下「新增設定」／「儲存變更」才寫入後端。 */
export function WizardDetailsStep({ wizard }: WizardDetailsStepProps) {
  const { draft, errors, updateField, check } = wizard;
  const { limits } = useLlmCatalog();
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
        maxLength={limits.config_name_max_length}
      />
      <TextField
        id={DRAFT_FIELD_INPUT_IDS.timeout_seconds}
        label="逾時（秒）"
        isOptional
        inputMode="numeric"
        value={draft.timeout_seconds}
        onChange={(value) => updateField("timeout_seconds", value)}
        placeholder={String(limits.default_timeout_seconds)}
        error={errors.timeout_seconds}
        hint={limits.timeout_hint}
      />
      <section
        aria-labelledby="wizard-summary-heading"
        className="flex flex-col gap-2"
      >
        <h3 id="wizard-summary-heading" className="text-headline">
          確認設定
        </h3>
        {/* 摘要由後端依表單內容產生；表單剛修改、檢查結果尚未回來時暫時留空 */}
        <SummaryList rows={check?.result.summary_rows ?? []} />
      </section>
    </div>
  );
}
