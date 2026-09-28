import { useEffect, useEffectEvent, useState } from "react";

import {
  type AvailableModel,
  queryAvailableModels,
  queryLocalModels,
} from "@/lib/api/availableModels";
import { toErrorMessage } from "@/lib/api/client";
import type { LlmProvider } from "@/lib/api/llmConfigs";
import type { ModelListPlan } from "@/lib/availableModels";
import { MODEL_LIST_DEBOUNCE_MS } from "@/lib/constants";

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

type ActivePlan = Exclude<ModelListPlan, { kind: "blocked" }>;

async function requestModelList(
  plan: ActivePlan,
  signal: AbortSignal,
): Promise<ModelListResult> {
  if (plan.kind === "local") {
    const result = await queryLocalModels(plan.query, signal);
    const detection = { provider: result.provider, apiBase: result.api_base };
    return { status: "ready", models: result.models, detection };
  }
  const result = await queryAvailableModels(plan.query, signal);
  return { status: "ready", models: result.models, detection: null };
}

/** 查詢失敗轉為錯誤結果；被中止（條件已改變）時回傳 `null` 不更新畫面。 */
async function loadModelList(
  plan: ActivePlan,
  signal: AbortSignal,
): Promise<ModelListResult | null> {
  try {
    return await requestModelList(plan, signal);
  } catch (error) {
    return signal.aborted
      ? null
      : { status: "error", message: toErrorMessage(error) };
  }
}

/** 查詢條件停止變動一段時間後才生效；以序列化字串比較，避免物件參考不同造成重複查詢。 */
function useSettledPlan(plan: ModelListPlan, planKey: string) {
  const [settled, setSettled] = useState({ key: planKey, plan });
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSettled((previous) =>
        previous.key === planKey ? previous : { key: planKey, plan },
      );
    }, MODEL_LIST_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [planKey, plan]);
  return settled;
}

type StoredResult = { requestKey: string; value: ModelListResult };

/** 送出查詢並保存結果；結果含本地伺服器偵測時通知呼叫端（非同步回呼，不在 render 中更新狀態）。 */
function useModelListRequest(
  settled: { key: string; plan: ModelListPlan },
  requestKey: string,
  onDetected: ((detection: LocalDetection) => void) | undefined,
): StoredResult | null {
  const [result, setResult] = useState<StoredResult | null>(null);
  const notifyDetected = useEffectEvent((detection: LocalDetection) => {
    onDetected?.(detection);
  });

  useEffect(() => {
    if (settled.plan.kind === "blocked") {
      return;
    }
    const controller = new AbortController();
    loadModelList(settled.plan, controller.signal).then((value) => {
      if (!value) {
        return;
      }
      setResult({ requestKey, value });
      if (value.status === "ready" && value.detection) {
        notifyDetected(value.detection);
      }
    });
    return () => controller.abort();
  }, [settled, requestKey]);

  return result;
}

/**
 * 依連線資訊自動查詢可用模型；條件改變時重新查詢並中止上一個請求。
 *
 * @param onDetected 本地模型偵測到伺服器類型與實際位址時呼叫，讓表單立即套用
 */
export function useAvailableModels(
  plan: ModelListPlan,
  onDetected?: (detection: LocalDetection) => void,
): { state: ModelListState; reload: () => void } {
  const planKey = JSON.stringify(plan);
  const settled = useSettledPlan(plan, planKey);
  const [reloadCount, setReloadCount] = useState(0);
  const requestKey = `${reloadCount}:${settled.key}`;
  const result = useModelListRequest(settled, requestKey, onDetected);

  const state = resolveState(plan, planKey === settled.key, result, requestKey);
  return { state, reload: () => setReloadCount((count) => count + 1) };
}

function resolveState(
  plan: ModelListPlan,
  isSettled: boolean,
  result: StoredResult | null,
  requestKey: string,
): ModelListState {
  if (plan.kind === "blocked") {
    return { status: "blocked", reason: plan.reason };
  }
  const isCurrent = isSettled && result?.requestKey === requestKey;
  return isCurrent && result ? result.value : { status: "loading" };
}
