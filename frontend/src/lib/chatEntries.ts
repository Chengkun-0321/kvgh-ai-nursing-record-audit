import type {
  ChatDoneEvent,
  ChatMessage,
  ChatStreamEvent,
} from "@/lib/api/llmChat";
import { formatSeconds } from "@/lib/format";

export type ChatEntryStatus = "streaming" | "done" | "stopped" | "error";

/** 畫面上的一則對話；對話歷史只存在前端，重新整理頁面即清除。 */
export type ChatEntry = {
  id: string;
  role: ChatMessage["role"];
  content: string;
  status: ChatEntryStatus;
  result?: ChatDoneEvent;
  errorMessage?: string;
};

// 串流結束卻沒有收到 done／error 事件（例如連線中斷）
const INTERRUPTED_MESSAGE = "回應中斷，請再試一次";

function createEntry(role: ChatEntry["role"], content: string): ChatEntry {
  const status = role === "user" ? "done" : "streaming";
  return { id: crypto.randomUUID(), role, content, status };
}

/** 使用者送出的訊息。 */
export function createUserEntry(text: string): ChatEntry {
  return createEntry("user", text);
}

/** 等待模型回應的空白訊息。 */
export function createReplyEntry(): ChatEntry {
  return createEntry("assistant", "");
}

/** 更新指定訊息。 */
export function updateEntry(
  entries: ChatEntry[],
  entryId: string,
  patch: Partial<ChatEntry>,
): ChatEntry[] {
  return entries.map((entry) =>
    entry.id === entryId ? { ...entry, ...patch } : entry,
  );
}

/** 把一個串流事件套用到回應訊息。 */
export function applyChatEvent(
  entries: ChatEntry[],
  replyId: string,
  event: ChatStreamEvent,
): ChatEntry[] {
  return entries.map((entry) => {
    if (entry.id !== replyId) {
      return entry;
    }
    if (event.type === "delta") {
      return { ...entry, content: entry.content + event.text };
    }
    if (event.type === "done") {
      return { ...entry, status: "done", result: event };
    }
    return { ...entry, status: "error", errorMessage: event.message };
  });
}

/** 串流結束後仍在「回應中」的訊息視為中斷。 */
export function settleReply(
  entries: ChatEntry[],
  replyId: string,
): ChatEntry[] {
  return entries.map((entry) =>
    entry.id === replyId && entry.status === "streaming"
      ? { ...entry, status: "error", errorMessage: INTERRUPTED_MESSAGE }
      : entry,
  );
}

function isUsableReply(entry: ChatEntry | undefined): boolean {
  const isFinished = entry?.status === "done" || entry?.status === "stopped";
  return entry?.role === "assistant" && isFinished && entry.content !== "";
}

/**
 * 組成送給模型的對話歷史：只保留「使用者訊息＋成功回應」的完整一問一答，
 * 失敗的提問不送出，避免連續兩則使用者訊息。
 */
export function toChatHistory(entries: ChatEntry[]): ChatMessage[] {
  return entries.flatMap((entry, index) => {
    const reply = entries[index + 1];
    if (entry.role !== "user" || !reply || !isUsableReply(reply)) {
      return [];
    }
    return [
      { role: "user", content: entry.content },
      { role: "assistant", content: reply.content },
    ];
  });
}

/**
 * 回應完成後的說明，例如
 * 「openai/gpt-5.3-codex・總耗時 2.4 秒・首字 0.5 秒・輸入 12／輸出 41 tokens・System prompt v3」。
 */
export function describeChatResult(result: ChatDoneEvent): string {
  const parts = [result.model, `總耗時 ${formatSeconds(result.latency_ms)}`];
  if (result.first_token_ms !== null) {
    parts.push(`首字 ${formatSeconds(result.first_token_ms)}`);
  }
  if (result.prompt_tokens !== null && result.completion_tokens !== null) {
    parts.push(
      `輸入 ${result.prompt_tokens}／輸出 ${result.completion_tokens} tokens`,
    );
  }
  if (result.system_prompt_version !== null) {
    parts.push(`System prompt v${result.system_prompt_version}`);
  }
  return parts.join("・");
}
