import { describe, expect, it } from "vitest";

import {
  applyChatEvent,
  type ChatEntry,
  createReplyEntry,
  createUserEntry,
  describeChatResult,
  settleReply,
  toChatHistory,
  updateEntry,
} from "@/lib/chatEntries";

function exchange(question: string, answer: string): ChatEntry[] {
  const reply = createReplyEntry();
  const entries = [createUserEntry(question), reply];
  const streamed = applyChatEvent(entries, reply.id, {
    type: "delta",
    text: answer,
  });
  return applyChatEvent(streamed, reply.id, {
    type: "done",
    model: "openai/test",
    latency_ms: 1200,
    first_token_ms: 300,
    prompt_tokens: 10,
    completion_tokens: 5,
    system_prompt_version: null,
  });
}

describe("applyChatEvent", () => {
  it("逐段累加回應文字，完成時標記為 done", () => {
    const [, reply] = exchange("你好", "嗨");

    expect(reply?.content).toBe("嗨");
    expect(reply?.status).toBe("done");
  });

  it("error 事件保留錯誤訊息", () => {
    const reply = createReplyEntry();

    const [updated] = applyChatEvent([reply], reply.id, {
      type: "error",
      message: "逾時",
    });

    expect(updated).toMatchObject({ status: "error", errorMessage: "逾時" });
  });
});

describe("settleReply", () => {
  it("沒有收到結束事件的回應視為中斷", () => {
    const reply = createReplyEntry();

    const [settled] = settleReply([reply], reply.id);

    expect(settled?.status).toBe("error");
  });
});

describe("toChatHistory", () => {
  it("只保留成功的一問一答，略過失敗的提問", () => {
    const failedReply = createReplyEntry();
    const failed = updateEntry(
      [createUserEntry("失敗的問題"), failedReply],
      failedReply.id,
      { status: "error", errorMessage: "x" },
    );

    const history = toChatHistory([...exchange("第一題", "答一"), ...failed]);

    expect(history).toEqual([
      { role: "user", content: "第一題" },
      { role: "assistant", content: "答一" },
    ]);
  });
});

describe("describeChatResult", () => {
  it("列出模型、耗時與 token 用量", () => {
    expect(
      describeChatResult({
        type: "done",
        model: "openai/test",
        latency_ms: 2400,
        first_token_ms: 500,
        prompt_tokens: 12,
        completion_tokens: 41,
        system_prompt_version: null,
      }),
    ).toBe("openai/test・總耗時 2.4 秒・首字 0.5 秒・輸入 12／輸出 41 tokens");
  });

  it("有共用 system prompt 時附上版本", () => {
    expect(
      describeChatResult({
        type: "done",
        model: "openai/test",
        latency_ms: 2400,
        first_token_ms: null,
        prompt_tokens: null,
        completion_tokens: null,
        system_prompt_version: 3,
      }),
    ).toBe("openai/test・總耗時 2.4 秒・System prompt v3");
  });
});
