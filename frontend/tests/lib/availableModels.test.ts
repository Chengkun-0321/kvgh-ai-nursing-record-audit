import { describe, expect, it } from "vitest";

import type { LlmConfig } from "@/lib/api/llmConfigs";

import { planModelList } from "@/lib/availableModels";
import { createEmptyDraft, type LlmConfigDraft } from "@/lib/llmConfigForm";

const STORED_LOCAL: LlmConfig = {
  id: "local-1",
  name: "LM Studio",
  provider: "openai_compatible",
  model: "qwen3-8b",
  api_base: "http://localhost:1234/v1",
  api_key_hint: "loc…0000",
  has_api_key: true,
  timeout_seconds: 60,
  is_active: false,
  created_at: "2026-09-28T00:00:00Z",
  updated_at: "2026-09-28T00:00:00Z",
};

function draftOf(fields: Partial<LlmConfigDraft>): LlmConfigDraft {
  return { ...createEmptyDraft(), ...fields };
}

describe("planModelList：雲端服務", () => {
  it("雲端服務沒有金鑰時不查詢，並說明原因", () => {
    const plan = planModelList(null, draftOf({ provider: "openai" }), false);

    expect(plan).toEqual({
      kind: "blocked",
      reason: "請先回上一步填寫 API 金鑰。",
    });
  });

  it("ChatGPT 訂閱登入後即可查詢此帳號的模型，不需要金鑰", () => {
    const plan = planModelList(null, draftOf({ provider: "chatgpt" }), true);

    expect(plan.kind).toBe("remote");
  });

  it("ChatGPT 訂閱尚未登入時不查詢，提示先登入", () => {
    const plan = planModelList(null, draftOf({ provider: "chatgpt" }), false);

    expect(plan).toMatchObject({ kind: "blocked" });
  });
});

describe("planModelList：本地模型", () => {
  it("本地模型留空位址時交給後端使用 Ollama 預設位址", () => {
    const plan = planModelList(null, draftOf({ provider: "ollama" }), false);

    expect(plan).toEqual({
      kind: "local",
      query: { api_base: null, api_key: null, config_id: null },
    });
  });

  it("本地模型的已儲存金鑰在 Ollama 與 OpenAI 相容之間可沿用", () => {
    const plan = planModelList(
      STORED_LOCAL,
      draftOf({ provider: "ollama", apiBase: "http://localhost:1234" }),
      false,
    );

    expect(plan).toMatchObject({
      kind: "local",
      query: { config_id: "local-1" },
    });
  });

  it("位址格式錯誤時不查詢", () => {
    const plan = planModelList(
      null,
      draftOf({ provider: "ollama", apiBase: "localhost" }),
      false,
    );

    expect(plan.kind).toBe("blocked");
  });
});
