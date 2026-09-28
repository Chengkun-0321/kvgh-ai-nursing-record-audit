import { useState } from "react";

import type { LlmConfig } from "@/lib/api/llmConfigs";
import {
  DRAFT_FIELD_INPUT_IDS,
  getFirstErrorField,
  type LlmConfigDraft,
  type LlmConfigDraftErrors,
  saveLlmConfigDraft,
} from "@/lib/llmConfigForm";
import {
  applyProviderChoice,
  suggestConfigName,
  validateStep,
  WIZARD_STEPS,
  type WizardStep,
} from "@/lib/llmConfigWizard";
import { type ProviderChoice, toProviderChoice } from "@/lib/llmProviders";

import { useAsyncAction } from "./useAsyncAction";
import type { LocalDetection } from "./useAvailableModels";
import { useLlmConfigDraft } from "./useLlmConfigDraft";

type WizardOptions = {
  /** 編輯中的設定；`null` 為新增 */
  config: LlmConfig | null;
  onSaved: (config: LlmConfig, isNew: boolean) => Promise<void>;
};

export type LlmConfigWizard = {
  config: LlmConfig | null;
  step: WizardStep;
  stepIndex: number;
  /** 1 為前進、-1 為返回，決定換頁動畫方向 */
  direction: 1 | -1;
  draft: LlmConfigDraft;
  errors: LlmConfigDraftErrors;
  /** 使用者選定的服務類型；新增時尚未選擇為 `null` */
  choice: ProviderChoice | null;
  updateField: ReturnType<typeof useLlmConfigDraft>["updateField"];
  chooseProvider: (choice: ProviderChoice) => void;
  selectModel: (model: string) => void;
  /** 套用本地伺服器偵測結果（實際類型與位址），查到清單即套用 */
  applyDetection: (detection: LocalDetection) => void;
  goNext: () => Promise<void>;
  goBack: () => void;
  isSaving: boolean;
  saveError: string | null;
};

const LAST_STEP_INDEX = WIZARD_STEPS.length - 1;

function stepAt(index: number): WizardStep {
  const step = WIZARD_STEPS[index] ?? WIZARD_STEPS[0];
  if (!step) {
    throw new Error("WIZARD_STEPS 不可為空");
  }
  return step;
}

function focusFirstError(errors: LlmConfigDraftErrors): boolean {
  const field = getFirstErrorField(errors);
  if (field) {
    document.getElementById(DRAFT_FIELD_INPUT_IDS[field])?.focus();
  }
  return field !== undefined;
}

type DraftState = ReturnType<typeof useLlmConfigDraft>;

type StepNavigation = {
  stepIndex: number;
  direction: 1 | -1;
  moveTo: (index: number) => void;
};

function useStepNavigation(): StepNavigation {
  const [stepIndex, setStepIndex] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);

  function moveTo(index: number) {
    setDirection(index > stepIndex ? 1 : -1);
    setStepIndex(index);
  }

  return { stepIndex, direction, moveTo };
}

type DraftActionsInput = {
  config: LlmConfig | null;
  draftState: DraftState;
  moveTo: (index: number) => void;
};

/** 選服務類型（選完直接進下一步）與從清單選模型。 */
function useDraftActions({ config, draftState, moveTo }: DraftActionsInput) {
  const [hasChosenProvider, setHasChosenProvider] = useState(config !== null);
  const { updateDraft, setErrors } = draftState;

  function chooseProvider(choice: ProviderChoice) {
    updateDraft((previous) => applyProviderChoice(previous, choice, config));
    setErrors({});
    setHasChosenProvider(true);
    moveTo(1);
  }

  function selectModel(model: string) {
    updateDraft((previous) => ({ ...previous, model }));
    setErrors({});
  }

  function applyDetection({ provider, apiBase }: LocalDetection) {
    updateDraft((previous) =>
      previous.provider === provider && previous.apiBase === apiBase
        ? previous
        : { ...previous, provider, apiBase },
    );
  }

  return { hasChosenProvider, chooseProvider, selectModel, applyDetection };
}

type AdvanceInput = WizardOptions & {
  draftState: DraftState;
  navigation: StepNavigation;
};

/** 「下一步」：檢查本步欄位，最後一步則儲存。 */
function useAdvance({ config, onSaved, draftState, navigation }: AdvanceInput) {
  const save = useAsyncAction();
  const { draft, updateField, setErrors } = draftState;
  const step = stepAt(navigation.stepIndex);

  async function goNext() {
    const stepErrors = validateStep(step.id, config, draft);
    setErrors(stepErrors);
    if (focusFirstError(stepErrors)) {
      return;
    }
    if (navigation.stepIndex < LAST_STEP_INDEX) {
      // 進入最後一步時，預設以「服務類型・模型」命名，可再修改
      if (step.id === "model" && !draft.name.trim()) {
        updateField("name", suggestConfigName(draft));
      }
      navigation.moveTo(navigation.stepIndex + 1);
      return;
    }
    const result = await save.run(() => saveLlmConfigDraft(config, draft));
    if (result.ok) {
      await onSaved(result.value, config === null);
    }
  }

  return { goNext, isSaving: save.isPending, saveError: save.errorMessage };
}

/** 逐步新增／編輯模型設定：每一步只檢查該步的欄位，最後一步才儲存。 */
export function useLlmConfigWizard(options: WizardOptions): LlmConfigWizard {
  const draftState = useLlmConfigDraft(options.config);
  const navigation = useStepNavigation();
  const actions = useDraftActions({
    config: options.config,
    draftState,
    moveTo: navigation.moveTo,
  });
  const advance = useAdvance({ ...options, draftState, navigation });

  return {
    config: options.config,
    step: stepAt(navigation.stepIndex),
    stepIndex: navigation.stepIndex,
    direction: navigation.direction,
    draft: draftState.draft,
    errors: draftState.errors,
    choice: actions.hasChosenProvider
      ? toProviderChoice(draftState.draft.provider)
      : null,
    updateField: draftState.updateField,
    chooseProvider: actions.chooseProvider,
    selectModel: actions.selectModel,
    applyDetection: actions.applyDetection,
    goBack: () => navigation.moveTo(Math.max(0, navigation.stepIndex - 1)),
    ...advance,
  };
}
