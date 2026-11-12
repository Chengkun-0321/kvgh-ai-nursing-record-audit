import { useEffect, useState } from "react";

import type { LlmConfig } from "@/lib/api/llmConfigs";
import {
  checkLlmConfigDraft,
  type LlmConfigDraftCheckResult,
} from "@/lib/api/llmProviders";
import { DRAFT_CHECK_DEBOUNCE_MS } from "@/lib/constants";
import type { LlmConfigDraft } from "@/lib/llmConfigForm";

/** 後端檢查結果，以及被檢查的那份表單內容（組模型查詢請求時用同一份，避免前後不一致）。 */
export type DraftCheck = {
  result: LlmConfigDraftCheckResult;
  checkedDraft: LlmConfigDraft;
  /** 是否就是目前表單內容的結果；表單剛改變、新結果尚未回來時為 false（仍沿用上一次結果） */
  isCurrent: boolean;
};

type StoredCheck = Omit<DraftCheck, "isCurrent"> & { key: string };

/**
 * 表單停止變動一段時間後，請後端檢查整份表單（不顯示錯誤，只取摘要、建議名稱與模型查詢方式）。
 * 新結果回來前沿用上一次結果（`isCurrent` 為 false），畫面不會每打一個字就閃回載入中；
 * 從未取得過結果時為 `null`。
 */
export function useDraftCheck(
  config: LlmConfig | null,
  draft: LlmConfigDraft,
  recheckKey: string,
): DraftCheck | null {
  const configId = config?.id ?? null;
  const draftJson = JSON.stringify(draft);
  const key = `${recheckKey}:${configId}:${draftJson}`;
  const [stored, setStored] = useState<StoredCheck | null>(null);

  // 以序列化內容作為依賴：物件參考改變但內容相同時不重新檢查
  useEffect(() => {
    const controller = new AbortController();
    const checkedDraft = JSON.parse(draftJson) as LlmConfigDraft;
    const timer = window.setTimeout(() => {
      checkLlmConfigDraft(
        { ...checkedDraft, config_id: configId, step_id: null },
        controller.signal,
      )
        .then((result) => setStored({ key, result, checkedDraft }))
        // 檢查失敗（含被中止）時維持「尚未取得」；按下一步時會再檢查一次並顯示錯誤
        .catch(() => undefined);
    }, DRAFT_CHECK_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key, configId, draftJson]);

  return stored ? { ...stored, isCurrent: stored.key === key } : null;
}
