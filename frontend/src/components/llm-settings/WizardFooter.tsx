"use client";

import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
} from "@/components/ui/controlStyles";
import { WarningCircleIcon } from "@/components/ui/icons";
import type { LlmConfigWizard } from "@/hooks/useLlmConfigWizard";
import { WIZARD_STEPS } from "@/lib/llmConfigWizard";

type WizardFooterProps = {
  wizard: LlmConfigWizard;
  onCancel: () => void;
};

function primaryLabel(wizard: LlmConfigWizard): string {
  if (wizard.stepIndex < WIZARD_STEPS.length - 1) {
    return "下一步";
  }
  if (wizard.isSaving) {
    return "儲存中…";
  }
  return wizard.config ? "儲存變更" : "新增設定";
}

/** 工作表底部：第 1 步為「取消」，之後為「上一步」；主要按鈕為「下一步」，最後一步儲存。 */
export function WizardFooter({ wizard, onCancel }: WizardFooterProps) {
  const isFirstStep = wizard.stepIndex === 0;
  // 新增時必須先選服務類型（點卡片即前進），不能直接按下一步
  const isNextBlocked = isFirstStep && wizard.choice === null;

  return (
    <footer className="flex flex-col gap-3 border-t border-separator px-5 pt-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:px-6 sm:pb-5">
      {wizard.saveError && (
        <p
          role="alert"
          className="flex items-start gap-1.5 text-body text-danger"
        >
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0"
          />
          {wizard.saveError}
        </p>
      )}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={isFirstStep ? onCancel : wizard.goBack}
          className={BUTTON_SECONDARY}
        >
          {isFirstStep ? "取消" : "上一步"}
        </button>
        <button
          type="button"
          onClick={wizard.goNext}
          disabled={isNextBlocked || wizard.isSaving}
          className={`${BUTTON_PRIMARY} ml-auto`}
        >
          {primaryLabel(wizard)}
        </button>
      </div>
    </footer>
  );
}
