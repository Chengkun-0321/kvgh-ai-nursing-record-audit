"use client";

import { AnimatePresence, motion } from "motion/react";

import type { ChatgptLogin } from "@/hooks/useChatgptLogin";
import type { LlmConfigWizard } from "@/hooks/useLlmConfigWizard";
import {
  FADE_FAST,
  WIZARD_STEP_OFFSET_PX,
  WIZARD_STEP_TRANSITION,
} from "@/lib/motion";

import { WizardConnectionStep } from "./WizardConnectionStep";
import { WizardDetailsStep } from "./WizardDetailsStep";
import { WizardModelStep } from "./WizardModelStep";
import { WizardProviderStep } from "./WizardProviderStep";

type WizardStepBodyProps = {
  wizard: LlmConfigWizard;
  login: ChatgptLogin;
};

function CurrentStep({ wizard, login }: WizardStepBodyProps) {
  switch (wizard.step.id) {
    case "provider":
      return (
        <WizardProviderStep
          selected={wizard.choice}
          isEditing={wizard.config !== null}
          onChoose={wizard.chooseProvider}
        />
      );
    case "connection":
      return <WizardConnectionStep wizard={wizard} login={login} />;
    case "model":
      return <WizardModelStep wizard={wizard} login={login} />;
    case "details":
      return <WizardDetailsStep wizard={wizard} />;
  }
}

/** 目前步驟的內容；前進時由右側滑入、返回時由左側滑入，減少動態時只淡入。 */
export function WizardStepBody({ wizard, login }: WizardStepBodyProps) {
  const offset = wizard.direction * WIZARD_STEP_OFFSET_PX;
  return (
    <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain px-5 pb-5 sm:px-6">
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={wizard.step.id}
          initial={{ opacity: 0, x: offset }}
          animate={{ opacity: 1, x: 0 }}
          // 退場只做短淡出，新步驟不必等舊內容滑完
          exit={{ opacity: 0, transition: FADE_FAST }}
          transition={WIZARD_STEP_TRANSITION}
        >
          <CurrentStep wizard={wizard} login={login} />
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
