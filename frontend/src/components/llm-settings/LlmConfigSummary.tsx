"use client";

import { useId } from "react";

import { BUTTON_PRIMARY } from "@/components/ui/controlStyles";
import { PencilSimpleIcon } from "@/components/ui/icons";
import type { ChatgptLogin } from "@/hooks/useChatgptLogin";
import type { LlmConfig } from "@/lib/api/llmConfigs";
import { describeConfig } from "@/lib/llmConfigSummary";

import { ChatgptLoginPanel } from "./ChatgptLoginPanel";
import { DeleteConfigButton } from "./DeleteConfigButton";
import { SummaryList } from "./SummaryList";

type LlmConfigSummaryProps = {
  config: LlmConfig;
  login: ChatgptLogin;
  onEdit: () => void;
  onDeleted: (config: LlmConfig) => Promise<void>;
};

/** 選取中設定的摘要：編輯開啟逐步工作表；ChatGPT 訂閱設定另顯示登入狀態。 */
export function LlmConfigSummary({
  config,
  login,
  onEdit,
  onDeleted,
}: LlmConfigSummaryProps) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <h2 id={headingId} className="min-w-0 flex-1 truncate text-headline">
          {config.name}
        </h2>
        {config.is_active && (
          <span className="shrink-0 rounded-full bg-surface px-2 py-0.5 text-caption font-semibold text-accent-strong ring-1 ring-accent-strong/35">
            使用中
          </span>
        )}
      </div>
      <SummaryList rows={describeConfig(config)} />
      {config.provider === "chatgpt" && <ChatgptLoginPanel login={login} />}
      <div className="flex flex-wrap items-start gap-2">
        <button type="button" onClick={onEdit} className={BUTTON_PRIMARY}>
          <PencilSimpleIcon aria-hidden="true" className="size-4.5" />
          編輯設定
        </button>
        <DeleteConfigButton config={config} onDeleted={onDeleted} />
      </div>
    </section>
  );
}
