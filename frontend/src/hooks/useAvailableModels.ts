import { useEffect, useEffectEvent, useState } from "react";

import {
  type AvailableModel,
  queryAvailableModels,
  queryLocalModels,
} from "@/lib/api/availableModels";
import { toErrorMessage } from "@/lib/api/client";
import type { LlmProvider } from "@/lib/api/llmConfigs";
import type { ModelListRequest } from "@/lib/availableModels";

/** 本地模型偵測到的伺服器類型與實際可用位址。 */
export type LocalDetection = { provider: LlmProvider; apiBase: string };

type ModelListResult =
  | {
      status: "ready";
      models: AvailableModel[];
      detection: LocalDetection | null;
    }
  | { status: "error"; message: string };

export type ModelListState =
  | { status: "blocked"; reason: string }
  | { status: "loading" }
  | ModelListResult;

type ActiveRequest = Extract<ModelListRequest, { kind: "local" | "remote" }>;

async function requestModelList(
  request: ActiveRequest,
  signal: AbortSignal,
): Promise<ModelListResult> {
  if (request.kind === "local") {
    const result = await queryLocalModels(request.query, signal);
    const detection = { provider: result.provider, apiBase: result.api_base };
    return { status: "ready", models: result.models, detection };
  }
  const result = await queryAvailableModels(request.query, signal);
  return { status: "ready", models: result.models, detection: null };
}

/** 查詢失敗轉為錯誤結果；被中止（條件已改變）時回傳 `null` 不更新畫面。 */
async function loadModelList(
  request: ActiveRequest,
  signal: AbortSignal,
): Promise<ModelListResult | null> {
  try {
    return await requestModelList(request, signal);
  } catch (error) {
    return signal.aborted
      ? null
      : { status: "error", message: toErrorMessage(error) };
  }
}

type StoredResult = { requestKey: string; value: ModelListResult };

function isActiveRequest(request: ModelListRequest): request is ActiveRequest {
  return request.kind === "local" || request.kind === "remote";
}

/**
 * 送出查詢並保存結果；結果含本地伺服器偵測時通知呼叫端（非同步回呼，不在 render 中更新狀態）。
 * 以序列化的請求內容作為依賴：物件參考改變但內容相同時不重新查詢。
 */
function useModelListRequest(
  requestJson: string,
  requestKey: string,
  onDetected: ((detection: LocalDetection) => void) | undefined,
): StoredResult | null {
  const [result, setResult] = useState<StoredResult | null>(null);
  const notifyDetected = useEffectEvent((detection: LocalDetection) => {
    onDetected?.(detection);
  });

  useEffect(() => {
    const request = JSON.parse(requestJson) as ModelListRequest;
    if (!isActiveRequest(request)) {
      return;
    }
    const controller = new AbortController();
    loadModelList(request, controller.signal).then((value) => {
      if (!value) {
        return;
      }
      setResult({ requestKey, value });
      if (value.status === "ready" && value.detection) {
        notifyDetected(value.detection);
      }
    });
    return () => controller.abort();
  }, [requestJson, requestKey]);

  return result;
}

/**
 * 依後端決定的查詢方式取得可用模型；條件改變時重新查詢並中止上一個請求。
 * 防抖已在表單檢查（`useDraftCheck`）處理，這裡收到新請求就直接查詢。
 *
 * @param onDetected 本地模型偵測到伺服器類型與實際位址時呼叫，讓表單立即套用
 */
export function useAvailableModels(
  request: ModelListRequest,
  onDetected?: (detection: LocalDetection) => void,
): { state: ModelListState; reload: () => void } {
  const [reloadCount, setReloadCount] = useState(0);
  const requestJson = JSON.stringify(request);
  const requestKey = `${reloadCount}:${requestJson}`;
  const result = useModelListRequest(requestJson, requestKey, onDetected);

  return {
    state: resolveState(request, result, requestKey),
    reload: () => setReloadCount((count) => count + 1),
  };
}

function resolveState(
  request: ModelListRequest,
  result: StoredResult | null,
  requestKey: string,
): ModelListState {
  if (request.kind === "blocked") {
    return { status: "blocked", reason: request.reason };
  }
  // pending：表單檢查結果尚未回來，畫面顯示載入中
  const isCurrent = result?.requestKey === requestKey;
  return isCurrent && result ? result.value : { status: "loading" };
}
