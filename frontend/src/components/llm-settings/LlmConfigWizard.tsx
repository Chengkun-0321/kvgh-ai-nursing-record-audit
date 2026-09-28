"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useRef } from "react";

import { XIcon } from "@/components/ui/icons";
import type { ChatgptLogin } from "@/hooks/useChatgptLogin";
import { useLlmConfigWizard } from "@/hooks/useLlmConfigWizard";
import type { LlmConfig } from "@/lib/api/llmConfigs";
import { WIZARD_STEPS } from "@/lib/llmConfigWizard";
import {
  FADE_SCRIM,
  PANEL_TRANSITION,
  WIZARD_SHEET_MOTION,
} from "@/lib/motion";

import { WizardFooter } from "./WizardFooter";
import { WizardStepBody } from "./WizardStepBody";
import { WizardStepProgress } from "./WizardStepProgress";

type WizardRequest = {
  /** 編輯中的設定；`null` 為新增 */
  config: LlmConfig | null;
};

type LlmConfigWizardProps = {
  request: WizardRequest | null;
  login: ChatgptLogin;
  onClose: () => void;
  onSaved: (config: LlmConfig, isNew: boolean) => Promise<void>;
};

type WizardSheetProps = Omit<LlmConfigWizardProps, "request"> &
  WizardRequest & { titleId: string };

function WizardSheet({
  config,
  login,
  onClose,
  onSaved,
  titleId,
}: WizardSheetProps) {
  const wizard = useLlmConfigWizard({ config, onSaved });
  const headingRef = useRef<HTMLHeadingElement>(null);

  // 換步驟後把焦點移到新標題，螢幕報讀會念出目前步驟
  useEffect(() => {
    if (wizard.stepIndex > 0) {
      headingRef.current?.focus();
    }
  }, [wizard.stepIndex]);

  return (
    <motion.div
      {...WIZARD_SHEET_MOTION}
      transition={PANEL_TRANSITION}
      className="glass relative flex w-full flex-col overflow-hidden shadow-float max-sm:h-dvh sm:max-h-[min(46rem,calc(100dvh-2rem))] sm:max-w-xl sm:rounded-panel"
    >
      <header className="flex items-start gap-3 px-5 pt-[calc(env(safe-area-inset-top)+1.25rem)] sm:px-6 sm:pt-6">
        <div className="min-w-0 flex-1">
          <p className="truncate text-footnote font-semibold text-ink-secondary">
            {config ? `編輯「${config.name}」` : "新增模型"}・步驟{" "}
            {wizard.stepIndex + 1}／{WIZARD_STEPS.length}
          </p>
          <h2
            ref={headingRef}
            id={titleId}
            tabIndex={-1}
            className="text-title outline-none"
          >
            {wizard.step.title}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="關閉，不儲存變更"
          className="grid size-11 shrink-0 pressable place-items-center rounded-full text-ink-secondary focus-ring hover:bg-fill"
        >
          <XIcon weight="bold" aria-hidden="true" className="size-5" />
        </button>
      </header>
      <WizardStepProgress currentIndex={wizard.stepIndex} />
      <WizardStepBody wizard={wizard} login={login} />
      <WizardFooter wizard={wizard} onCancel={onClose} />
    </motion.div>
  );
}

/**
 * 新增／編輯模型設定的逐步工作表：原生 `<dialog>` 提供 Esc 關閉、背景 inert 與焦點還原；
 * 點背景不關閉，避免誤觸丟失已輸入的內容。
 */
export function LlmConfigWizard({
  request,
  login,
  onClose,
  onSaved,
}: LlmConfigWizardProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const isOpen = request !== null;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (isOpen && dialog && !dialog.open) {
      dialog.showModal();
    }
  }, [isOpen]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      className="fixed inset-0 m-0 size-full max-h-none max-w-none overflow-hidden border-0 bg-transparent p-0 backdrop:bg-transparent"
    >
      <AnimatePresence onExitComplete={() => dialogRef.current?.close()}>
        {isOpen && (
          <motion.div
            key="scrim"
            aria-hidden="true"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={FADE_SCRIM}
            className="absolute inset-0 bg-scrim"
          />
        )}
        {isOpen && (
          <div
            key="sheet"
            className="absolute inset-0 flex items-center justify-center sm:p-4"
          >
            <WizardSheet
              config={request.config}
              login={login}
              onClose={onClose}
              onSaved={onSaved}
              titleId={titleId}
            />
          </div>
        )}
      </AnimatePresence>
    </dialog>
  );
}
