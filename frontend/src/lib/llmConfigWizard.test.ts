import { describe, expect, it } from "vitest";

import type { LlmConfig } from "@/lib/api/llmConfigs";

import { createEmptyDraft, type LlmConfigDraft } from "./llmConfigForm";
import {
  applyProviderChoice,
  suggestConfigName,
  validateStep,
} from "./llmConfigWizard";

const STORED_CODEX: LlmConfig = {
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
};

function draftOf(fields: Partial<LlmConfigDraft>): LlmConfigDraft {
  return { ...createEmptyDraft(), ...fields };
}

describe("validateStep", () => {
  it("只檢查該步驟負責的欄位", () => {
    const draft = draftOf({ provider: "gemini" });

    expect(Object.keys(validateStep("connection", null, draft))).toEqual([
      "apiKey",
    ]);
    expect(Object.keys(validateStep("model", null, draft))).toEqual(["model"]);
  });

  it("編輯時沿用已儲存的金鑰，連線設定可直接通過", () => {
    const draft = draftOf({ provider: "openai" });

    expect(validateStep("connection", STORED_CODEX, draft)).toEqual({});
  });
});

describe("applyProviderChoice：切換", () => {
  it("換成其他服務類型時清空模型與金鑰，保留名稱", () => {
    const draft = draftOf({
      name: "我的設定",
      provider: "openai",
      model: "gpt-5.3-codex",
      apiKey: "sk-x",
    });

    const next = applyProviderChoice(draft, "gemini", null);

    expect(next).toMatchObject({
      name: "我的設定",
      provider: "gemini",
      model: "",
      apiKey: "",
    });
  });

  it("選擇本地模型時先假設為 Ollama", () => {
    expect(applyProviderChoice(draftOf({}), "local", null).provider).toBe(
      "ollama",
    );
  });
});

describe("applyProviderChoice：保留與還原", () => {
  it("編輯時換回原本的服務類型會還原原本的模型", () => {
    const switched = applyProviderChoice(
      draftOf({ provider: "gemini" }),
      "openai",
      STORED_CODEX,
    );

    expect(switched.model).toBe("gpt-5.3-codex");
  });

  it("選擇目前的服務類型時保留已輸入的內容", () => {
    const draft = draftOf({ provider: "openai", apiKey: "sk-typed" });

    expect(applyProviderChoice(draft, "openai", null)).toBe(draft);
  });
});

describe("suggestConfigName", () => {
  it("以服務類型與模型組成預設名稱", () => {
    expect(
      suggestConfigName(draftOf({ provider: "ollama", model: "qwen3:8b" })),
    ).toBe("本地模型（Ollama）・qwen3:8b");
  });
});
