"use client";

import { useEffect, useRef } from "react";

import { BUTTON_SECONDARY } from "@/components/ui/controlStyles";
import { InfoIcon } from "@/components/ui/icons";
import { useChatStream } from "@/hooks/useChatStream";
import type { LlmConfig } from "@/lib/api/llmConfigs";
import { CHAT_MAX_MESSAGES } from "@/lib/constants";
import { getProviderOption } from "@/lib/llmProviders";

import { ChatComposer } from "./ChatComposer";
import { ChatMessageBubble } from "./ChatMessageBubble";

type ChatTestPanelProps = {
  /** 測試對象；`null` 表示尚未有任何設定 */
  config: LlmConfig | null;
};

// 一次送出一問，歷史加上新提問不可超過上限
const LIMIT_REACHED_MESSAGE = `已達 ${CHAT_MAX_MESSAGES / 2} 輪對話上限，請先清除對話。`;

function ChatSession({ config }: { config: LlmConfig }) {
  const { entries, isStreaming, send, stop, clear } = useChatStream(config.id);
  const logRef = useRef<HTMLUListElement>(null);
  const isLimitReached = entries.length + 1 > CHAT_MAX_MESSAGES;

  // 新內容出現時捲到最底；直接設定位置，不做平滑捲動
  useEffect(() => {
    const log = logRef.current;
    if (log) {
      log.scrollTop = log.scrollHeight;
    }
  }, [entries]);

  return (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-headline">測試對話</h2>
          <p className="truncate text-footnote text-ink-secondary">
            對象：{config.name}（{getProviderOption(config.provider).label}・
            {config.model}）
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            stop();
            clear();
          }}
          disabled={entries.length === 0}
          className={BUTTON_SECONDARY}
        >
          清除對話
        </button>
      </div>
      <ul
        ref={logRef}
        role="log"
        aria-label="測試對話內容"
        aria-busy={isStreaming}
        className="flex min-h-64 flex-1 flex-col gap-3 overflow-y-auto overscroll-contain rounded-card bg-surface p-4 shadow-card"
      >
        {entries.length === 0 && (
          <li className="m-auto max-w-xs text-center text-body text-ink-secondary">
            輸入訊息測試連線，回應會逐字顯示在這裡。
          </li>
        )}
        {entries.map((entry) => (
          <ChatMessageBubble key={entry.id} entry={entry} />
        ))}
      </ul>
      <ChatComposer
        isStreaming={isStreaming}
        disabledReason={isLimitReached ? LIMIT_REACHED_MESSAGE : null}
        onSend={send}
        onStop={stop}
      />
    </>
  );
}

/**
 * 測試對話：以已儲存的設定直接呼叫模型並串流顯示回應；切換測試對象時清除對話。
 */
export function ChatTestPanel({ config }: ChatTestPanelProps) {
  return (
    <section
      aria-label="測試對話"
      className="glass relative flex flex-col gap-4 rounded-panel p-4 shadow-float lg:sticky lg:top-toolbar lg:h-[calc(100dvh-var(--spacing-toolbar)-1rem)] lg:p-5"
    >
      {config ? (
        <ChatSession key={config.id} config={config} />
      ) : (
        <div className="m-auto max-w-xs text-center">
          <h2 className="text-headline">測試對話</h2>
          <p className="mt-1 text-body text-ink-secondary">
            新增模型設定後，即可在這裡輸入訊息測試連線。
          </p>
        </div>
      )}
      <p className="flex items-start gap-1.5 text-footnote text-ink-secondary">
        <InfoIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        以左側選取的已儲存設定測試。對話內容會送往所選服務，請勿輸入病患資料。
      </p>
    </section>
  );
}
