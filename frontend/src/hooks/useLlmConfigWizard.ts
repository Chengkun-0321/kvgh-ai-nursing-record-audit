import { useState } from "react";

import { useLlmCatalog } from "@/components/llm-settings/LlmCatalogContext";
import type { LlmConfig } from "@/lib/api/llmConfigs";
import {
  checkLlmConfigDraft,
  type LlmConfigDraftCheckResult,
  type LlmProviderCatalog,
  type ProviderChoice,
  type WizardStep,
} from "@/lib/api/llmProviders";
import {
  DRAFT_FIELD_INPUT_IDS,
  type LlmConfigDraft,
  type LlmConfigDraftErrors,
  saveLlmConfigDraft,
  toDraftCheck,
} from "@/lib/llmConfigForm";
import { applyProviderChoice, toProviderChoice } from "@/lib/llmConfigWizard";

import { useAsyncAction } from "./useAsyncAction";
import type { LocalDetection } from "./useAvailableModels";
import { type DraftCheck, useDraftCheck } from "./useDraftCheck";
import { useLlmConfigDraft } from "./useLlmConfigDraft";

type WizardOptions = {
  /** 編輯中的設定；`null` 為新增 */
  config: LlmConfig | null;
  onSaved: (config: LlmConfig, isNew: boolean) => Promise<void>;
  /** 會影響檢查結果的外部狀態（ChatGPT 登入狀態）；改變時重新請後端檢查 */
  recheckKey: string;
};

export type LlmConfigWizard = {
  config: LlmConfig | null;
  steps: readonly WizardStep[];
  step: WizardStep;
  stepIndex: number;
  /** 1 為前進、-1 為返回，決定換頁動畫方向 */
  direction: 1 | -1;
  draft: LlmConfigDraft;
  errors: LlmConfigDraftErrors;
  /** 後端對目前表單的檢查結果（摘要、模型查詢方式）；表單剛改變時為 `null` */
  check: DraftCheck | null;
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

type DraftState = ReturnType<typeof useLlmConfigDraft>;

function stepAt(steps: readonly WizardStep[], index: number): WizardStep {
  const step = steps[index] ?? steps[0];
  if (!step) {
    throw new Error("精靈步驟不可為空");
  }
  return step;
}

/** 依後端回傳的順序，焦點移到第一個錯誤欄位；有錯誤時回傳 `true`。 */
function focusFirstError(result: LlmConfigDraftCheckResult): boolean {
  const first = result.errors[0];
  if (first) {
    document.getElementById(DRAFT_FIELD_INPUT_IDS[first.field])?.focus();
  }
  return first !== undefined;
}

function toErrorMap(result: LlmConfigDraftCheckResult): LlmConfigDraftErrors {
  return Object.fromEntries(
    result.errors.map((error) => [error.field, error.message]),
  );
}

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
  catalog: LlmProviderCatalog;
  config: LlmConfig | null;
  draftState: DraftState;
  moveTo: (index: number) => void;
};

/** 選服務類型（選完直接進下一步）與從清單選模型。 */
function useDraftActions(input: DraftActionsInput) {
  const { catalog, config, draftState, moveTo } = input;
  const [hasChosenProvider, setHasChosenProvider] = useState(config !== null);
  const { updateDraft, setErrors } = draftState;

  function chooseProvider(choice: ProviderChoice) {
    updateDraft((previous) =>
      applyProviderChoice(catalog, previous, choice, config),
    );
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
      previous.provider === provider && previous.api_base === apiBase
        ? previous
        : { ...previous, provider, api_base: apiBase },
    );
  }

  const choice = hasChosenProvider
    ? toProviderChoice(catalog, draftState.draft.provider)
    : null;
  return { choice, chooseProvider, selectModel, applyDetection };
}

type AdvanceInput = WizardOptions & {
  steps: readonly WizardStep[];
  draftState: DraftState;
  navigation: StepNavigation;
};

/** 「下一步」：請後端檢查本步欄位，通過才前進；最後一步則儲存。 */
function useAdvance(input: AdvanceInput) {
  const { config, onSaved, steps, draftState, navigation } = input;
  const save = useAsyncAction();
  const { draft, updateField, setErrors } = draftState;
  const step = stepAt(steps, navigation.stepIndex);
  const isLastStep = navigation.stepIndex >= steps.length - 1;

  async function goNext() {
    const checked = await save.run(() =>
      checkLlmConfigDraft(toDraftCheck(config, draft, step.step_id)),
    );
    if (!checked.ok) return;
    setErrors(toErrorMap(checked.value));
    if (focusFirstError(checked.value)) return;
    if (!isLastStep) {
      // 進入最後一步時，預設以後端建議的「服務類型・模型」命名，可再修改
      if (step.step_id === "model" && !draft.name.trim()) {
        updateField("name", checked.value.suggested_name);
      }
      navigation.moveTo(navigation.stepIndex + 1);
      return;
    }
    const result = await save.run(() => saveLlmConfigDraft(config, draft));
    if (result.ok) await onSaved(result.value, config === null);
  }

  return { goNext, isSaving: save.isPending, saveError: save.errorMessage };
}

/** 逐步新增／編輯模型設定：每一步請後端檢查該步的欄位，最後一步才儲存。 */
export function useLlmConfigWizard(options: WizardOptions): LlmConfigWizard {
  const catalog = useLlmCatalog();
  const steps = catalog.wizard_steps;
  const draftState = useLlmConfigDraft(options.config);
  const navigation = useStepNavigation();
  const { draft } = draftState;
  const check = useDraftCheck(options.config, draft, options.recheckKey);
  const actions = useDraftActions({
    catalog,
    config: options.config,
    draftState,
    moveTo: navigation.moveTo,
  });

  return {
    config: options.config,
    steps,
    step: stepAt(steps, navigation.stepIndex),
    stepIndex: navigation.stepIndex,
    direction: navigation.direction,
    draft,
    errors: draftState.errors,
    check,
    updateField: draftState.updateField,
    ...actions,
    goBack: () => navigation.moveTo(Math.max(0, navigation.stepIndex - 1)),
    ...useAdvance({ ...options, steps, draftState, navigation }),
  };
}
