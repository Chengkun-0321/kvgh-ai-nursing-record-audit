import { readSseData } from "@/lib/sse";
import type { components } from "@/types/api";

import { ApiError, apiRequest } from "./client";

export type ChatMessage = components["schemas"]["ChatMessage"];
export type ChatDoneEvent = components["schemas"]["ChatDoneEvent"];
export type ChatStreamEvent =
  | components["schemas"]["ChatDeltaEvent"]
  | ChatDoneEvent
  | components["schemas"]["ChatErrorEvent"];

const STREAM_EVENT_TYPES: ReadonlySet<string> = new Set([
  "delta",
  "done",
  "error",
]);

/** 解析一個串流事件；無法辨識的內容回傳 `null` 並略過。 */
export function parseChatStreamEvent(data: string): ChatStreamEvent | null {
  try {
    const event: unknown = JSON.parse(data);
    if (
      typeof event === "object" &&
      event !== null &&
      "type" in event &&
      typeof event.type === "string" &&
      STREAM_EVENT_TYPES.has(event.type)
    ) {
      // 事件結構由後端 ChatStreamEvent schema 保證
      return event as ChatStreamEvent;
    }
  } catch {
    // 非 JSON 的 data 行不屬於本協定，略過
  }
  return null;
}

/**
 * 以指定設定進行測試對話，逐一產生串流事件。
 *
 * @param configId 要測試的模型設定
 * @param messages 完整對話歷史，最後一則為使用者訊息
 * @param signal 用於「停止」的中止訊號
 */
export async function* streamLlmChat(
  configId: string,
  messages: ChatMessage[],
  signal: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const response = await apiRequest(`/api/v1/llm-configs/${configId}/chat`, {
    method: "POST",
    body: JSON.stringify({ messages }),
    headers: { Accept: "text/event-stream" },
    signal,
  });
  if (!response.body) {
    throw new ApiError(response.status, "後端沒有回傳串流內容，請稍後再試");
  }
  for await (const data of readSseData(response.body)) {
    const event = parseChatStreamEvent(data);
    if (event) {
      yield event;
    }
  }
}
