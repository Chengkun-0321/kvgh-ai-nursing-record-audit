import type { components } from "@/types/api";

import { apiJson } from "./client";

export type AvailableModel = components["schemas"]["AvailableModel"];
export type AvailableModelsQuery =
  components["schemas"]["AvailableModelsQuery"];
export type AvailableModelsRead = components["schemas"]["AvailableModelsRead"];
export type LocalModelsQuery = components["schemas"]["LocalModelsQuery"];
export type LocalModelsRead = components["schemas"]["LocalModelsRead"];

const BASE_PATH = "/api/v1/available-models";

/** 查詢雲端服務（Codex、Gemini、ChatGPT 訂閱）目前可用的模型；金鑰放在 body。 */
export function queryAvailableModels(
  query: AvailableModelsQuery,
  signal: AbortSignal,
): Promise<AvailableModelsRead> {
  return apiJson<AvailableModelsRead>(BASE_PATH, {
    method: "POST",
    body: JSON.stringify(query),
    signal,
  });
}

/** 偵測本地伺服器類型（Ollama／OpenAI 相容）並列出可用模型。 */
export function queryLocalModels(
  query: LocalModelsQuery,
  signal: AbortSignal,
): Promise<LocalModelsRead> {
  return apiJson<LocalModelsRead>(`${BASE_PATH}/local`, {
    method: "POST",
    body: JSON.stringify(query),
    signal,
  });
}
