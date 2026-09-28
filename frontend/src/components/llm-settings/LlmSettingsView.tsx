"use client";

import { type ReactNode, useState } from "react";

import { useAsyncAction } from "@/hooks/useAsyncAction";
import { useChatgptLogin } from "@/hooks/useChatgptLogin";
import { useLlmConfigs } from "@/hooks/useLlmConfigs";
import type { ChatgptAuthStatus } from "@/lib/api/chatgptAuth";
import { toErrorMessage } from "@/lib/api/client";
import { activateLlmConfig, type LlmConfig } from "@/lib/api/llmConfigs";
import type { LlmSystemPrompt } from "@/lib/api/llmSystemPrompts";
import { getInitialSelectedId, resolveSelectedConfig } from "@/lib/llmSettings";

import { ChatTestPanel } from "./ChatTestPanel";
import { LlmConfigList } from "./LlmConfigList";
import { LlmConfigSummary } from "./LlmConfigSummary";
import { LlmConfigWizard } from "./LlmConfigWizard";
import { type Notice, SettingsNotice } from "./SettingsNotice";
import { SystemPromptPanel } from "./SystemPromptPanel";

type LlmSettingsViewProps = {
  /** 頁首（由 Server Component 提供），放在左欄頂端，讓右側對話面板能填滿視窗高度 */
  header: ReactNode;
  initialConfigs: LlmConfig[];
  initialChatgptStatus: ChatgptAuthStatus;
  initialSystemPrompt: LlmSystemPrompt;
};

/**
 * LLM 模型設定頁：左側管理多組設定（同一時間只有一組使用中）與共用 system prompt，
 * 右側以對話測試選取的設定。
 * 每次變更後重新讀取後端列表，畫面永遠與 DB 一致。
 */
export function LlmSettingsView({
  header,
  initialConfigs,
  initialChatgptStatus,
  initialSystemPrompt,
}: LlmSettingsViewProps) {
  const { configs, reload } = useLlmConfigs(initialConfigs);
  const login = useChatgptLogin(initialChatgptStatus);
  const activation = useAsyncAction();
  const [selectedId, setSelectedId] = useState(() =>
    getInitialSelectedId(initialConfigs),
  );
  const [activatingId, setActivatingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  // 開啟中的逐步工作表：config 為 null 表示新增
  const [wizard, setWizard] = useState<{ config: LlmConfig | null } | null>(
    null,
  );
  const selected = resolveSelectedConfig(configs, selectedId);

  function showNotice(next: Notice | null) {
    activation.clearError();
    setNotice(next);
  }

  async function refresh(): Promise<LlmConfig[] | null> {
    try {
      return await reload();
    } catch (error) {
      showNotice({ tone: "error", message: toErrorMessage(error) });
      return null;
    }
  }

  async function handleSaved(config: LlmConfig, isNew: boolean) {
    setWizard(null);
    await refresh();
    setSelectedId(config.id);
    const activeSuffix = isNew && config.is_active ? "，並設為使用中" : "";
    const action = isNew ? "已新增" : "已儲存";
    showNotice({
      tone: "success",
      message: `${action}「${config.name}」${activeSuffix}`,
    });
  }

  async function handleDeleted(config: LlmConfig) {
    const latest = await refresh();
    setSelectedId(latest ? getInitialSelectedId(latest) : null);
    showNotice({ tone: "success", message: `已刪除「${config.name}」` });
  }

  async function handleActivate(config: LlmConfig) {
    if (config.is_active) {
      return;
    }
    setActivatingId(config.id);
    const result = await activation.run(() => activateLlmConfig(config.id));
    setActivatingId(null);
    if (result.ok) {
      await refresh();
      showNotice({
        tone: "success",
        message: `已將「${config.name}」設為使用中`,
      });
    }
  }

  function selectConfig(configId: string) {
    setSelectedId(configId);
    showNotice(null);
  }

  const shownNotice: Notice | null = activation.errorMessage
    ? { tone: "error", message: activation.errorMessage }
    : notice;

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-4 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] xl:grid-cols-[minmax(0,30rem)_minmax(0,1fr)]">
      <div className="flex flex-col gap-4">
        {header}
        <div className="glass relative flex flex-col gap-4 rounded-panel p-4 shadow-float lg:p-5">
          <LlmConfigList
            configs={configs}
            selectedId={selected?.id ?? null}
            activatingId={activatingId}
            onSelect={selectConfig}
            onActivate={handleActivate}
            onCreate={() => setWizard({ config: null })}
          />
          <SettingsNotice notice={shownNotice} />
          {selected && (
            <LlmConfigSummary
              config={selected}
              login={login}
              onEdit={() => setWizard({ config: selected })}
              onDeleted={handleDeleted}
            />
          )}
        </div>
        <SystemPromptPanel initialSystemPrompt={initialSystemPrompt} />
      </div>
      <ChatTestPanel config={selected} />
      <LlmConfigWizard
        request={wizard}
        login={login}
        onClose={() => setWizard(null)}
        onSaved={handleSaved}
      />
    </div>
  );
}
