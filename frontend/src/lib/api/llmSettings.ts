import { type ChatgptAuthStatus, getChatgptAuthStatus } from "./chatgptAuth";
import { toErrorMessage } from "./client";
import { type LlmConfig, listLlmConfigs } from "./llmConfigs";
import {
  getCurrentSystemPrompt,
  type LlmSystemPrompt,
} from "./llmSystemPrompts";

export type LlmSettingsLoadResult =
  | {
      ok: true;
      configs: LlmConfig[];
      chatgptStatus: ChatgptAuthStatus;
      systemPrompt: LlmSystemPrompt;
    }
  | { ok: false; message: string };

/** 讀取設定頁所需的資料；後端無法連線時回傳可顯示的訊息，不讓頁面整個失敗。 */
export async function loadLlmSettings(): Promise<LlmSettingsLoadResult> {
  try {
    const [configs, chatgptStatus, systemPrompt] = await Promise.all([
      listLlmConfigs(),
      getChatgptAuthStatus(),
      getCurrentSystemPrompt(),
    ]);
    return { ok: true, configs, chatgptStatus, systemPrompt };
  } catch (error) {
    return { ok: false, message: toErrorMessage(error) };
  }
}
