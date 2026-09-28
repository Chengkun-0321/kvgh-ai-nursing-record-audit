import { useState } from "react";

import { useAsyncAction } from "@/hooks/useAsyncAction";
import type { LlmSystemPrompt } from "@/lib/api/llmSystemPrompts";
import {
  isSystemPromptChanged,
  saveSystemPromptDraft,
} from "@/lib/systemPrompt";

export type SystemPromptEditor = {
  saved: LlmSystemPrompt;
  draft: string;
  isChanged: boolean;
  isSaving: boolean;
  errorMessage: string | null;
  /** 最近一次儲存成功的版本；編輯後清除，避免訊息與內容不符 */
  justSaved: LlmSystemPrompt | null;
  setDraft: (value: string) => void;
  save: () => Promise<void>;
};

/** 共用 system prompt 的草稿與儲存；測試對話一律使用已儲存的版本。 */
export function useSystemPromptEditor(
  initial: LlmSystemPrompt,
): SystemPromptEditor {
  const [saved, setSaved] = useState(initial);
  const [draft, setDraftValue] = useState(initial.content);
  const [justSaved, setJustSaved] = useState<LlmSystemPrompt | null>(null);
  const action = useAsyncAction();

  function setDraft(value: string) {
    setDraftValue(value);
    setJustSaved(null);
    action.clearError();
  }

  async function save() {
    // 失敗（含 409 已有較新版本）時保留草稿，讓使用者可以先複製
    const result = await action.run(() => saveSystemPromptDraft(draft, saved));
    if (result.ok) {
      setSaved(result.value);
      setJustSaved(result.value);
    }
  }

  return {
    saved,
    draft,
    isChanged: isSystemPromptChanged(draft, saved),
    isSaving: action.isPending,
    errorMessage: action.errorMessage,
    justSaved,
    setDraft,
    save,
  };
}
