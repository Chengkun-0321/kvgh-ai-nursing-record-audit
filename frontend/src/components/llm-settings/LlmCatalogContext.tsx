"use client";

import { createContext, type ReactNode, use } from "react";

import type { LlmProvider } from "@/lib/api/llmConfigs";
import type {
  LlmProviderCatalog,
  LlmProviderOption,
} from "@/lib/api/llmProviders";

const LlmCatalogContext = createContext<LlmProviderCatalog | null>(null);

/** 把後端提供的服務類型目錄交給設定頁底下的元件。 */
export function LlmCatalogProvider({
  catalog,
  children,
}: {
  catalog: LlmProviderCatalog;
  children: ReactNode;
}) {
  return <LlmCatalogContext value={catalog}>{children}</LlmCatalogContext>;
}

/** 取得服務類型目錄；只能在 `LlmCatalogProvider` 底下使用。 */
export function useLlmCatalog(): LlmProviderCatalog {
  const catalog = use(LlmCatalogContext);
  if (!catalog) {
    throw new Error("useLlmCatalog 必須在 LlmCatalogProvider 底下使用");
  }
  return catalog;
}

/** 在目錄中查出服務類型的顯示名稱、欄位規則與範例。 */
export function findProviderOption(
  catalog: LlmProviderCatalog,
  provider: LlmProvider,
): LlmProviderOption {
  const option = catalog.providers.find((item) => item.provider === provider);
  if (!option) {
    throw new Error(`服務類型目錄缺少 ${provider}`);
  }
  return option;
}

/** 依服務類型查出顯示名稱、欄位規則與範例。 */
export function useProviderOption(provider: LlmProvider): LlmProviderOption {
  return findProviderOption(useLlmCatalog(), provider);
}
