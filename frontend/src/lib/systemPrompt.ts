import {
  type LlmSystemPrompt,
  saveSystemPrompt,
} from "@/lib/api/llmSystemPrompts";
import { formatShortDateTime } from "@/lib/format";

/** 後端儲存前會去除首尾空白，比較時以相同規則判斷是否有變更。 */
export function isSystemPromptChanged(
  draft: string,
  saved: LlmSystemPrompt,
): boolean {
  return draft.trim() !== saved.content;
}

/** 目前使用的版本，例如「目前版本 v3・更新於 09/28 10:31」。 */
export function describeSavedSystemPrompt(saved: LlmSystemPrompt): string {
  if (saved.version === null || saved.created_at === null) {
    return "尚未設定";
  }
  const state = saved.content === "" ? "（不使用）" : "";
  return `目前版本 v${saved.version}${state}・更新於 ${formatShortDateTime(saved.created_at)}`;
}

/** 儲存成功的訊息。 */
export function describeSavedResult(saved: LlmSystemPrompt): string {
  if (saved.content === "") {
    return `已清空（v${saved.version}），呼叫模型時不再帶 system prompt`;
  }
  return `已儲存為 v${saved.version}，之後的模型呼叫都會帶上這段指示`;
}

/** 儲存草稿：以畫面上的版本為基準；已有較新版本時後端回 409，不會覆寫。 */
export function saveSystemPromptDraft(
  draft: string,
  saved: LlmSystemPrompt,
): Promise<LlmSystemPrompt> {
  return saveSystemPrompt({
    content: draft.trim(),
    base_version: saved.version,
  });
}
