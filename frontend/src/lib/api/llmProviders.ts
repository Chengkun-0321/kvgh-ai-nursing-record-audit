import type { components } from "@/types/api";

import { apiJson } from "./client";

export type LlmProviderCatalog =
  components["schemas"]["LlmProviderCatalogRead"];
export type LlmProviderOption = components["schemas"]["LlmProviderOptionRead"];
export type ProviderChoice = components["schemas"]["ProviderChoice"];
export type WizardStep = components["schemas"]["WizardStepRead"];
export type WizardStepId = components["schemas"]["WizardStepId"];
export type FieldRequirement = components["schemas"]["FieldRequirement"];
export type DraftField = components["schemas"]["DraftField"];
export type LlmConfigDraftCheck = components["schemas"]["LlmConfigDraftCheck"];
export type LlmConfigDraftCheckResult =
  components["schemas"]["LlmConfigDraftCheckRead"];
export type ModelListPlan = components["schemas"]["ModelListPlanRead"];
export type SummaryRow = components["schemas"]["SummaryRowRead"];

/** 服務類型目錄、精靈步驟與各項上限（設定頁開啟時讀取一次）。 */
export function getLlmProviderCatalog(): Promise<LlmProviderCatalog> {
  return apiJson<LlmProviderCatalog>("/api/v1/llm-providers");
}

/**
 * 請後端檢查設定精靈的表單：逐欄錯誤、是否沿用已儲存金鑰、建議名稱、模型查詢方式與確認摘要。
 * 只檢查不儲存；表單含 API 金鑰，因此用 POST。
 */
export function checkLlmConfigDraft(
  payload: LlmConfigDraftCheck,
  signal?: AbortSignal,
): Promise<LlmConfigDraftCheckResult> {
  return apiJson<LlmConfigDraftCheckResult>(
    "/api/v1/llm-configs/draft-checks",
    { method: "POST", body: JSON.stringify(payload), signal },
  );
}
