import type { components } from "@/types/api";

import { apiJson } from "./client";

export type LlmSystemPrompt = components["schemas"]["LlmSystemPromptRead"];

const BASE_PATH = "/api/v1/llm-system-prompts";

/** 取得目前使用的共用 system prompt；尚未設定時 `version` 為 null、內容為空。 */
export function getCurrentSystemPrompt(): Promise<LlmSystemPrompt> {
  return apiJson<LlmSystemPrompt>(`${BASE_PATH}/current`);
}

export type LlmSystemPromptCreate =
  components["schemas"]["LlmSystemPromptCreate"];

/**
 * 儲存為新版本；空字串表示不使用 system prompt。
 * `base_version` 為開始編輯時的版本，已有較新版本時後端回 409，不會覆寫。
 */
export function saveSystemPrompt(
  payload: LlmSystemPromptCreate,
): Promise<LlmSystemPrompt> {
  return apiJson<LlmSystemPrompt>(BASE_PATH, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
