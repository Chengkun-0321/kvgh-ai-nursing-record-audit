import type {
  AvailableModelsQuery,
  LocalModelsQuery,
} from "@/lib/api/availableModels";
import type { LlmConfig } from "@/lib/api/llmConfigs";
import { isHttpUrl, type LlmConfigDraft } from "@/lib/llmConfigForm";
import { getProviderOption, isLocalProvider } from "@/lib/llmProviders";

/** 查詢模型清單的方式；缺少必要資訊時說明原因，不發出請求。 */
export type ModelListPlan =
  | { kind: "local"; query: LocalModelsQuery }
  | { kind: "remote"; query: AvailableModelsQuery }
  | { kind: "blocked"; reason: string };

/** 可沿用已儲存金鑰時回傳設定 ID；本地模型的兩種伺服器之間可互相沿用。 */
function storedKeyConfigId(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): string | null {
  if (!config?.has_api_key || draft.clearApiKey) {
    return null;
  }
  const isSameService = isLocalProvider(draft.provider)
    ? isLocalProvider(config.provider)
    : config.provider === draft.provider;
  return isSameService ? config.id : null;
}

function planLocal(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): ModelListPlan {
  const apiBase = draft.apiBase.trim();
  if (apiBase && !isHttpUrl(apiBase)) {
    return {
      kind: "blocked",
      reason: "伺服器位址格式正確後，會自動列出可用模型。",
    };
  }
  const query: LocalModelsQuery = {
    api_base: apiBase || null,
    api_key: draft.apiKey.trim() || null,
    config_id: storedKeyConfigId(config, draft),
  };
  return { kind: "local", query };
}

function planRemote(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
): ModelListPlan {
  const configId = storedKeyConfigId(config, draft);
  const apiKey = draft.apiKey.trim();
  const needsKey = getProviderOption(draft.provider).apiKey === "required";
  if (needsKey && !apiKey && !configId) {
    return { kind: "blocked", reason: "請先回上一步填寫 API 金鑰。" };
  }
  const query: AvailableModelsQuery = {
    provider: draft.provider,
    api_key: apiKey || null,
    config_id: configId,
  };
  return { kind: "remote", query };
}

const CHATGPT_SIGN_IN_REASON =
  "請先回上一步登入 ChatGPT 帳號，登入後會列出此帳號可用的模型。";

/**
 * 依表單目前的連線資訊決定如何查詢模型清單。
 *
 * @param config 編輯中的設定（新增時為 `null`），用於沿用已儲存的金鑰
 * @param isChatgptSignedIn ChatGPT 訂閱需先登入，才能查詢此帳號可用的模型
 */
export function planModelList(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
  isChatgptSignedIn: boolean,
): ModelListPlan {
  if (draft.provider === "chatgpt" && !isChatgptSignedIn) {
    return { kind: "blocked", reason: CHATGPT_SIGN_IN_REASON };
  }
  return isLocalProvider(draft.provider)
    ? planLocal(config, draft)
    : planRemote(config, draft);
}
