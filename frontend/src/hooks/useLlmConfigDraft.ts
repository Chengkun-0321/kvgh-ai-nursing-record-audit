import { useState } from "react";

import type { LlmConfig } from "@/lib/api/llmConfigs";
import {
  createEmptyDraft,
  draftFromConfig,
  type LlmConfigDraft,
  type LlmConfigDraftErrors,
} from "@/lib/llmConfigForm";

type LlmConfigDraftState = {
  draft: LlmConfigDraft;
  errors: LlmConfigDraftErrors;
  updateField: <K extends keyof LlmConfigDraft>(
    key: K,
    value: LlmConfigDraft[K],
  ) => void;
  /** 一次更新多個欄位（例如切換服務類型、套用偵測結果）。 */
  updateDraft: (update: (previous: LlmConfigDraft) => LlmConfigDraft) => void;
  setErrors: (errors: LlmConfigDraftErrors) => void;
};

/**
 * 模型設定的草稿狀態；以 `config` 初始化（`null` 為新增）。
 * 每次開啟逐步表單都重新掛載，不沿用上一次的草稿。
 */
export function useLlmConfigDraft(
  config: LlmConfig | null,
): LlmConfigDraftState {
  const [draft, setDraft] = useState(() =>
    config ? draftFromConfig(config) : createEmptyDraft(),
  );
  const [errors, setErrors] = useState<LlmConfigDraftErrors>({});

  function updateField<K extends keyof LlmConfigDraft>(
    key: K,
    value: LlmConfigDraft[K],
  ) {
    setDraft((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: undefined }));
  }

  return { draft, errors, updateField, updateDraft: setDraft, setErrors };
}
