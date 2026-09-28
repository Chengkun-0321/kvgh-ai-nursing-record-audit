import type { components } from "@/types/api";

import { apiJson, apiRequest } from "./client";

export type LlmConfig = components["schemas"]["LlmConfigRead"];
export type LlmConfigCreate = components["schemas"]["LlmConfigCreate"];
export type LlmConfigUpdate = components["schemas"]["LlmConfigUpdate"];
export type LlmProvider = components["schemas"]["LlmProvider"];

const BASE_PATH = "/api/v1/llm-configs";

/** 列出所有已儲存的模型設定（依建立時間）。 */
export function listLlmConfigs(): Promise<LlmConfig[]> {
  return apiJson<LlmConfig[]>(BASE_PATH);
}

/** 新增模型設定；不影響目前使用中的設定（第一筆除外）。 */
export function createLlmConfig(payload: LlmConfigCreate): Promise<LlmConfig> {
  return apiJson<LlmConfig>(BASE_PATH, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** 更新模型設定；`api_key` 未填表示沿用已儲存的金鑰。 */
export function updateLlmConfig(
  configId: string,
  payload: LlmConfigUpdate,
): Promise<LlmConfig> {
  return apiJson<LlmConfig>(`${BASE_PATH}/${configId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/** 刪除模型設定（使用中的設定會被後端拒絕）。 */
export async function deleteLlmConfig(configId: string): Promise<void> {
  await apiRequest(`${BASE_PATH}/${configId}`, { method: "DELETE" });
}

/** 把指定設定設為使用中，其他設定改為非使用中。 */
export function activateLlmConfig(configId: string): Promise<LlmConfig> {
  return apiJson<LlmConfig>(`${BASE_PATH}/${configId}/activate`, {
    method: "POST",
  });
}
