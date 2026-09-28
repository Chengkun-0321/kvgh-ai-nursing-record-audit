import { describe, expect, it } from "vitest";

import {
  createEmptyDraft,
  getFirstErrorField,
  type LlmConfigDraft,
  toCreatePayload,
  toUpdatePayload,
  validateDraft,
} from "./llmConfigForm";

function draftOf(fields: Partial<LlmConfigDraft>): LlmConfigDraft {
  return { ...createEmptyDraft(), name: "測試", model: "m", ...fields };
}

describe("validateDraft", () => {
  it("API 金鑰必填的服務類型，沒有已儲存的金鑰時要求輸入", () => {
    const errors = validateDraft(draftOf({ provider: "openai" }), false);

    expect(errors.apiKey).toBe("請輸入 API 金鑰");
  });

  it("已儲存金鑰時可留空", () => {
    expect(validateDraft(draftOf({ provider: "openai" }), true)).toEqual({});
  });

  it("OpenAI 相容伺服器必須填寫 API 位址且格式正確", () => {
    const missing = validateDraft(
      draftOf({ provider: "openai_compatible" }),
      false,
    );
    const invalid = validateDraft(
      draftOf({ provider: "openai_compatible", apiBase: "localhost:1234" }),
      false,
    );

    expect(missing.apiBase).toBe("請輸入 API 位址");
    expect(invalid.apiBase).toContain("http://");
  });

  it("逾時超出範圍時提示允許的範圍", () => {
    const errors = validateDraft(
      draftOf({ provider: "ollama", timeoutSeconds: "1" }),
      false,
    );

    expect(errors.timeoutSeconds).toBe("請輸入 5–600 的整數");
  });
});

describe("getFirstErrorField", () => {
  it("依逐步表單的順序（連線 → 模型 → 命名）找出第一個錯誤欄位", () => {
    const errors = validateDraft(
      draftOf({ name: "", model: "", provider: "ollama" }),
      false,
    );

    expect(getFirstErrorField(errors)).toBe("model");
  });
});

describe("toCreatePayload", () => {
  it("該服務類型用不到的欄位不送出，留空的逾時交給後端預設值", () => {
    const payload = toCreatePayload(
      draftOf({ provider: "chatgpt", apiKey: "sk-x", apiBase: "http://x" }),
    );

    expect(payload).toMatchObject({
      provider: "chatgpt",
      api_key: null,
      api_base: null,
      timeout_seconds: null,
    });
  });
});

describe("toUpdatePayload", () => {
  it("金鑰留空表示沿用，並帶上是否移除金鑰", () => {
    const payload = toUpdatePayload(
      draftOf({ provider: "openai_compatible", apiBase: "http://h/v1" }),
    );

    expect(payload).toMatchObject({ api_key: null, clear_api_key: false });
  });
});
