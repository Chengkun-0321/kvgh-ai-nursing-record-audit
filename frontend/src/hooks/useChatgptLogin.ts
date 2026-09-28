import { useEffect, useState } from "react";

import { toErrorMessage } from "@/lib/api/client";
import {
  type ChatgptAuthStatus,
  getChatgptAuthStatus,
  signOutChatgpt,
  startChatgptLogin,
} from "@/lib/api/chatgptAuth";
import { CHATGPT_LOGIN_POLL_MS } from "@/lib/constants";

import { useAsyncAction } from "./useAsyncAction";

/** 登入進行中時定期向後端確認是否已完成。 */
function useLoginPolling(
  isPending: boolean,
  onStatus: (status: ChatgptAuthStatus) => void,
  onError: (message: string) => void,
): void {
  useEffect(() => {
    if (!isPending) {
      return;
    }
    const timer = window.setInterval(() => {
      getChatgptAuthStatus()
        .then(onStatus)
        .catch((error: unknown) => onError(toErrorMessage(error)));
    }, CHATGPT_LOGIN_POLL_MS);
    return () => window.clearInterval(timer);
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
