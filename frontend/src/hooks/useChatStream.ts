import {
  type Dispatch,
  type SetStateAction,
  useEffect,
  useRef,
  useState,
} from "react";

import { toErrorMessage } from "@/lib/api/client";
import { type ChatMessage, streamLlmChat } from "@/lib/api/llmChat";
import {
  applyChatEvent,
  type ChatEntry,
  createReplyEntry,
  createUserEntry,
  settleReply,
  toChatHistory,
  updateEntry,
} from "@/lib/chatEntries";

type ChatTurn = {
  configId: string;
  messages: ChatMessage[];
  controller: AbortController;
  setEntries: Dispatch<SetStateAction<ChatEntry[]>>;
};

/** 送出一輪對話並把串流事件逐一寫入畫面；按下停止時保留已收到的內容。 */
async function runChatTurn({
  configId,
  messages,
  controller,
  setEntries,
}: ChatTurn): Promise<void> {
  const question = messages.at(-1)?.content ?? "";
  const reply = createReplyEntry();
  setEntries((previous) => [...previous, createUserEntry(question), reply]);
  try {
    const events = streamLlmChat(configId, messages, controller.signal);
    for await (const event of events) {
      setEntries((previous) => applyChatEvent(previous, reply.id, event));
    }
    setEntries((previous) => settleReply(previous, reply.id));
  } catch (error) {
    const patch: Partial<ChatEntry> = controller.signal.aborted
      ? { status: "stopped" }
      : { status: "error", errorMessage: toErrorMessage(error) };
    setEntries((previous) => updateEntry(previous, reply.id, patch));
  }
}

type ChatStream = {
  entries: ChatEntry[];
  isStreaming: boolean;
  send: (text: string) => Promise<void>;
  stop: () => void;
  clear: () => void;
};

/**
 * 測試對話：對話歷史只存在前端，每次送出完整歷史；可隨時停止。
 *
 * @param configId 要測試的模型設定
 */
export function useChatStream(configId: string): ChatStream {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  // 離開頁面或切換測試對象時中止進行中的回應
  useEffect(() => () => controllerRef.current?.abort(), []);

  async function send(text: string) {
    const controller = new AbortController();
    controllerRef.current = controller;
    setIsStreaming(true);
    const question: ChatMessage = { role: "user", content: text };
    const messages = [...toChatHistory(entries), question];
    await runChatTurn({ configId, messages, controller, setEntries });
    controllerRef.current = null;
    setIsStreaming(false);
  }

  function stop() {
    controllerRef.current?.abort();
  }

  return { entries, isStreaming, send, stop, clear: () => setEntries([]) };
}
