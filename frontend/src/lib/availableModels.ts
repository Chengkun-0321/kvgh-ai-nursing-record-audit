import type {
  AvailableModelsQuery,
  LocalModelsQuery,
} from "@/lib/api/availableModels";
import type { ModelListPlan } from "@/lib/api/llmProviders";
import type { LlmConfigDraft } from "@/lib/llmConfigForm";

/** 查詢模型清單的請求；是否可查、要不要沿用已儲存金鑰由後端的檢查結果決定。 */
export type ModelListRequest =
  | { kind: "local"; query: LocalModelsQuery }
  | { kind: "remote"; query: AvailableModelsQuery }
  | { kind: "blocked"; reason: string }
  | { kind: "pending" };

/**
 * 把後端回傳的查詢方式與目前表單內容組成請求（只組裝欄位，不做判斷）。
 *
 * @param plan 後端檢查結果中的 `model_list`；尚未取得時為 `null`
 */
export function toModelListRequest(
  plan: ModelListPlan | null,
  draft: LlmConfigDraft,
): ModelListRequest {
  if (!plan) {
    return { kind: "pending" };
  }
  if (plan.kind === "blocked") {
    return { kind: "blocked", reason: plan.reason ?? "" };
  }
  const api_key = draft.api_key.trim() || null;
  if (plan.kind === "local") {
    const api_base = draft.api_base.trim() || null;
    return {
      kind: "local",
      query: { api_base, api_key, config_id: plan.config_id },
    };
  }
  return {
    kind: "remote",
    query: { provider: draft.provider, api_key, config_id: plan.config_id },
  };
}
