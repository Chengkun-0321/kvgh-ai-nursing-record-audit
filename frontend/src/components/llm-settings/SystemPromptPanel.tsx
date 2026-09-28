"use client";

import { useId } from "react";

import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  INPUT_CLASS,
} from "@/components/ui/controlStyles";
import { InfoIcon } from "@/components/ui/icons";
import { useSystemPromptEditor } from "@/hooks/useSystemPromptEditor";
import type { LlmSystemPrompt } from "@/lib/api/llmSystemPrompts";
import { SYSTEM_PROMPT_MAX_CHARS } from "@/lib/constants";
import {
  describeSavedResult,
  describeSavedSystemPrompt,
} from "@/lib/systemPrompt";
import { cn } from "@/lib/utils";

import { type Notice, SettingsNotice } from "./SettingsNotice";

type SystemPromptPanelProps = {
  initialSystemPrompt: LlmSystemPrompt;
};

function toNotice(
  errorMessage: string | null,
  justSaved: LlmSystemPrompt | null,
): Notice | null {
  if (errorMessage) {
    return { tone: "error", message: errorMessage };
  }
  return justSaved
    ? { tone: "success", message: describeSavedResult(justSaved) }
    : null;
}

/**
 * 共用 system prompt：所有模型設定與稽核呼叫都先帶上這段指示。
 * 每次儲存為新版本，測試對話的資訊列會顯示所用的版本。
 */
export function SystemPromptPanel({
  initialSystemPrompt,
}: SystemPromptPanelProps) {
  const editor = useSystemPromptEditor(initialSystemPrompt);
  const headingId = useId();
  const hintId = useId();
  const inputId = useId();

  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-panel bg-surface p-4 shadow-card lg:p-5"
    >
      <div className="flex flex-col gap-1">
        <h2 id={headingId} className="text-headline">
          <label htmlFor={inputId}>共用 System Prompt</label>
        </h2>
        <p id={hintId} className="text-footnote text-ink-secondary">
          所有模型設定、測試對話與稽核呼叫都會先帶上這段指示；留空表示不使用（ChatGPT
          訂閱留空時會改用 Codex 內建指示）。
        </p>
      </div>
      <textarea
        id={inputId}
        value={editor.draft}
        onChange={(event) => editor.setDraft(event.target.value)}
        aria-describedby={hintId}
        maxLength={SYSTEM_PROMPT_MAX_CHARS}
        rows={6}
        spellCheck={false}
        placeholder="例：你是護理紀錄稽核助理，一律使用繁體中文回答，只根據提供的資料判斷。"
        className={cn(
          INPUT_CLASS,
          "field-sizing-content max-h-96 min-h-36 resize-none py-2.5",
        )}
      />
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-footnote text-ink-secondary">
        <span>{describeSavedSystemPrompt(editor.saved)}</span>
        <span className="tabular-nums">
          {editor.draft.length} / {SYSTEM_PROMPT_MAX_CHARS}
        </span>
      </div>
      {editor.isChanged && (
        <p className="flex items-start gap-1.5 text-footnote text-ink">
          <InfoIcon
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0 text-accent-strong"
          />
          有未儲存的變更；測試對話使用已儲存的版本。
        </p>
      )}
      <SettingsNotice
        notice={toNotice(editor.errorMessage, editor.justSaved)}
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => void editor.save()}
          disabled={!editor.isChanged || editor.isSaving}
          className={BUTTON_PRIMARY}
        >
          {editor.isSaving ? "儲存中…" : "儲存"}
        </button>
        <button
          type="button"
          onClick={() => editor.setDraft(editor.saved.content)}
          disabled={!editor.isChanged || editor.isSaving}
          className={BUTTON_SECONDARY}
        >
          捨棄變更
        </button>
      </div>
    </section>
  );
}
