import { describe, expect, it } from "vitest";

import type { LlmSystemPrompt } from "@/lib/api/llmSystemPrompts";

import {
  describeSavedResult,
  describeSavedSystemPrompt,
  isSystemPromptChanged,
} from "./systemPrompt";

const SAVED: LlmSystemPrompt = {
  version: 3,
  content: "一律使用繁體中文回答。",
  created_at: "2026-09-28T02:31:00Z",
};

describe("isSystemPromptChanged", () => {
  it("只差首尾空白時視為未變更", () => {
    expect(isSystemPromptChanged("  一律使用繁體中文回答。\n", SAVED)).toBe(
      false,
    );
  });

  it("內容不同時視為已變更", () => {
    expect(isSystemPromptChanged("只根據資料回答。", SAVED)).toBe(true);
  });
});

describe("describeSavedSystemPrompt", () => {
  it("顯示版本與台北時間", () => {
    expect(describeSavedSystemPrompt(SAVED)).toBe(
      "目前版本 v3・更新於 09/28 10:31",
    );
  });

  it("尚未儲存過", () => {
    expect(
      describeSavedSystemPrompt({
        version: null,
        content: "",
        created_at: null,
      }),
    ).toBe("尚未設定");
  });

  it("已清空的版本標示不使用", () => {
    expect(describeSavedSystemPrompt({ ...SAVED, content: "" })).toBe(
      "目前版本 v3（不使用）・更新於 09/28 10:31",
    );
  });
});

describe("describeSavedResult", () => {
  it("區分儲存與清空", () => {
    expect(describeSavedResult(SAVED)).toBe(
      "已儲存為 v3，之後的模型呼叫都會帶上這段指示",
    );
    expect(describeSavedResult({ ...SAVED, content: "" })).toBe(
      "已清空（v3），呼叫模型時不再帶 system prompt",
    );
  });
});
