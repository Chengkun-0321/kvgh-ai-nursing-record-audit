import { useEffect, useState } from "react";

import { toErrorMessage } from "@/lib/api/client";
import {
  type ChatgptAuthStatus,
  getChatgptAuthStatus,
  signOutChatgpt,
  startChatgptLogin,
} from "@/lib/api/chatgptAuth";
import { CHATGPT_LOGIN_POLL_MS } from "@/lib/constants";
import { pollUntilAborted } from "@/lib/pollLoop";

import { useAsyncAction } from "./useAsyncAction";

/** 登入進行中時定期向後端確認是否已完成；停止輪詢後，進行中請求的結果一律忽略。 */
function useLoginPolling(
  isPending: boolean,
  onStatus: (status: ChatgptAuthStatus) => void,
  onError: (message: string) => void,
): void {
  useEffect(() => {
    if (!isPending) {
      return;
    }
    const controller = new AbortController();
    const { signal } = controller;
    async function pollOnce() {
      try {
        const status = await getChatgptAuthStatus(signal);
        if (!signal.aborted) {
          onStatus(status);
        }
      } catch (error) {
        if (!signal.aborted) {
          onError(toErrorMessage(error));
        }
      }
    }
    void pollUntilAborted(pollOnce, CHATGPT_LOGIN_POLL_MS, signal);
    return () => controller.abort();
  }, [isPending, onStatus, onError]);
}

export type ChatgptLogin = {
  status: ChatgptAuthStatus;
  isBusy: boolean;
  errorMessage: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
};

/** ChatGPT 訂閱登入狀態與操作（裝置碼登入、登出）。 */
export function useChatgptLogin(
  initialStatus: ChatgptAuthStatus,
): ChatgptLogin {
  const [status, setStatus] = useState(initialStatus);
  const [pollError, setPollError] = useState<string | null>(null);
  const action = useAsyncAction();
  useLoginPolling(status.state === "pending", setStatus, setPollError);

  async function apply(request: () => Promise<ChatgptAuthStatus>) {
    setPollError(null);
    const result = await action.run(request);
    if (result.ok) {
      setStatus(result.value);
    }
  }

  return {
    status,
    isBusy: action.isPending,
    errorMessage: action.errorMessage ?? pollError,
    signIn: () => apply(startChatgptLogin),
    signOut: () => apply(signOutChatgpt),
  };
}
