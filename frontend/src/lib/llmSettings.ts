import type { LlmConfig } from "@/lib/api/llmConfigs";

/**
 * 決定左欄顯示摘要的設定：選取的設定已不存在（例如剛刪除）或尚未選取時，
 * 改選使用中的設定；沒有任何設定時為 `null`。
 */
export function resolveSelectedConfig(
  configs: readonly LlmConfig[],
  selectedId: string | null,
): LlmConfig | null {
  const selected = configs.find((config) => config.id === selectedId);
  return (
    selected ?? configs.find((config) => config.is_active) ?? configs[0] ?? null
  );
}

/** 頁面開啟時預設選取使用中的設定。 */
export function getInitialSelectedId(
  configs: readonly LlmConfig[],
): string | null {
  return resolveSelectedConfig(configs, null)?.id ?? null;
}
