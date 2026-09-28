"use client";

import { type FormEvent, type KeyboardEvent, useState } from "react";

import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  INPUT_CLASS,
} from "@/components/ui/controlStyles";
import { PaperPlaneRightIcon, StopIcon } from "@/components/ui/icons";
import { CHAT_MAX_MESSAGE_CHARS } from "@/lib/constants";
import { cn } from "@/lib/utils";

type ChatComposerProps = {
  isStreaming: boolean;
  /** 無法送出的原因（例如已達對話上限）；`null` 表示可以送出 */
  disabledReason: string | null;
  onSend: (text: string) => void;
  onStop: () => void;
};

/** 輸入框：Enter 送出、Shift+Enter 換行；輸入法選字中按 Enter 不會送出。 */
export function ChatComposer({
  isStreaming,
  disabledReason,
  onSend,
  onStop,
}: ChatComposerProps) {
  const [text, setText] = useState("");
  const canSend = !isStreaming && disabledReason === null && text.trim() !== "";

  function submit() {
    if (!canSend) {
      return;
    }
    onSend(text.trim());
    setText("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      onSubmit={(event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        submit();
      }}
      className="flex flex-col gap-2"
    >
      <label htmlFor="chat-test-input" className="sr-only">
        測試訊息
      </label>
      <div className="flex items-end gap-2">
        <textarea
          id="chat-test-input"
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          maxLength={CHAT_MAX_MESSAGE_CHARS}
          disabled={disabledReason !== null}
          placeholder="輸入訊息，Enter 送出、Shift+Enter 換行"
          className={cn(
            INPUT_CLASS,
            "field-sizing-content max-h-40 min-h-11 min-w-0 flex-1 resize-none py-2.5 disabled:bg-fill",
          )}
        />
        {isStreaming ? (
          <button type="button" onClick={onStop} className={BUTTON_SECONDARY}>
            <StopIcon weight="fill" aria-hidden="true" className="size-4.5" />
            停止
          </button>
        ) : (
          <button type="submit" disabled={!canSend} className={BUTTON_PRIMARY}>
            <PaperPlaneRightIcon aria-hidden="true" className="size-4.5" />
            送出
          </button>
        )}
      </div>
      {disabledReason && (
        <p className="text-footnote text-ink-secondary">{disabledReason}</p>
      )}
    </form>
  );
}
