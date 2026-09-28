import type { Metadata } from "next";
import { connection } from "next/server";

import { LlmSettingsView } from "@/components/llm-settings/LlmSettingsView";
import { WarningCircleIcon } from "@/components/ui/icons";
import { loadLlmSettings } from "@/lib/api/llmSettings";

export const metadata: Metadata = {
  title: "LLM 模型設定｜護理稽核系統",
};

// 每次開啟都向後端讀取已儲存的設定，不使用建置時的快照
export default async function LlmSettingsPage() {
  await connection();
  const result = await loadLlmSettings();

  const header = (
    <header>
      <p className="text-footnote font-semibold text-ink-secondary">設定</p>
      <h1 className="text-large-title">LLM 模型</h1>
      <p className="mt-1 text-body text-ink-secondary">
        可儲存多組模型設定，同一時間只使用一組；系統呼叫模型時一律使用「使用中」的設定。
      </p>
    </header>
  );

  if (result.ok) {
    return (
      <LlmSettingsView
        header={header}
        initialConfigs={result.configs}
        initialChatgptStatus={result.chatgptStatus}
        initialSystemPrompt={result.systemPrompt}
      />
    );
  }
  return (
    <div className="flex max-w-2xl flex-col gap-4">
      {header}
      <p
        role="alert"
        className="glass relative flex items-start gap-2 rounded-panel p-5 text-body text-ink shadow-float"
      >
        <WarningCircleIcon
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-danger"
        />
        {result.message}
      </p>
    </div>
  );
}
