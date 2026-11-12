import { describe, expect, it } from "vitest";

import type { LlmConfig } from "@/lib/api/llmConfigs";
import type { LlmProviderCatalog } from "@/lib/api/llmProviders";

import { createEmptyDraft, type LlmConfigDraft } from "./llmConfigForm";
import { applyProviderChoice } from "./llmConfigWizard";

// 驗證、建議名稱等規則已移到後端（backend/tests/api/v1/test_llm_draft_checks_api.py），
// 這裡只測切換服務類型時的表單狀態。目錄只放測試用得到的欄位。
const CATALOG = {
  providers: [
    { provider: "openai", choice: "openai" },
    { provider: "chatgpt", choice: "chatgpt" },
    { provider: "gemini", choice: "gemini" },
    { provider: "ollama", choice: "local" },
    { provider: "openai_compatible", choice: "local" },
  ],
  choices: [
    { choice: "openai", default_provider: "openai" },
    { choice: "chatgpt", default_provider: "chatgpt" },
    { choice: "gemini", default_provider: "gemini" },
    { choice: "local", default_provider: "ollama" },
  ],
} as unknown as LlmProviderCatalog;

const STORED_CODEX = {
  id: "c1",
  name: "Codex 正式",
  provider: "openai",
  model: "gpt-5.3-codex",
  api_base: null,
  api_key_hint: "sk-…abcd",
  has_api_key: true,
  timeout_seconds: 60,
  is_active: true,
  created_at: "2026-09-28T00:00:00Z",
  updated_at: "2026-09-28T00:00:00Z",
  provider_label: "Codex・API 金鑰",
  summary_rows: [],
} satisfies LlmConfig;

function draftOf(fields: Partial<LlmConfigDraft>): LlmConfigDraft {
  return { ...createEmptyDraft(), ...fields };
}

describe("applyProviderChoice：切換", () => {
  it("換成其他服務類型時清空模型與金鑰，保留名稱", () => {
    const draft = draftOf({
      name: "我的設定",
      provider: "openai",
      model: "gpt-5.3-codex",
      api_key: "sk-x",
    });

    const next = applyProviderChoice(CATALOG, draft, "gemini", null);

    expect(next).toMatchObject({
      name: "我的設定",
      provider: "gemini",
      model: "",
      api_key: "",
    });
  });

  it("選擇本地模型時套用後端指定的預設類型", () => {
    const next = applyProviderChoice(CATALOG, draftOf({}), "local", null);
    expect(next.provider).toBe("ollama");
  });
});

describe("applyProviderChoice：保留與還原", () => {
  it("編輯時換回原本的服務類型會還原原本的模型", () => {
    const switched = applyProviderChoice(
      CATALOG,
      draftOf({ provider: "gemini" }),
      "openai",
      STORED_CODEX,
    );

    expect(switched.model).toBe("gpt-5.3-codex");
  });

  it("選擇目前的服務類型時保留已輸入的內容", () => {
    const draft = draftOf({ provider: "openai", api_key: "sk-typed" });

    expect(applyProviderChoice(CATALOG, draft, "openai", null)).toBe(draft);
  });
});
