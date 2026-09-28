import { useState } from "react";

import { type LlmConfig, listLlmConfigs } from "@/lib/api/llmConfigs";

type LlmConfigsState = {
  configs: LlmConfig[];
  /** 重新向後端讀取設定列表（新增、更新、切換、刪除之後呼叫）。 */
  reload: () => Promise<LlmConfig[]>;
};

/**
 * 已儲存的模型設定列表：以 Server Component 讀到的資料為初始值，
 * 之後每次變更都重新向後端讀取，畫面永遠反映 DB 內容。
 */
export function useLlmConfigs(initialConfigs: LlmConfig[]): LlmConfigsState {
  const [configs, setConfigs] = useState(initialConfigs);

  async function reload(): Promise<LlmConfig[]> {
    const latest = await listLlmConfigs();
    setConfigs(latest);
    return latest;
  }

  return { configs, reload };
}
