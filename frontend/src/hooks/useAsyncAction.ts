import { useState } from "react";

import { toErrorMessage } from "@/lib/api/client";

export type ActionResult<T> = { ok: true; value: T } | { ok: false };

type AsyncAction = {
  isPending: boolean;
  errorMessage: string | null;
  run: <T>(action: () => Promise<T>) => Promise<ActionResult<T>>;
  clearError: () => void;
};

/**
 * 執行一個會呼叫後端的操作：追蹤進行中狀態，失敗時保留可顯示的繁中錯誤訊息。
 */
export function useAsyncAction(): AsyncAction {
  const [isPending, setIsPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function run<T>(action: () => Promise<T>): Promise<ActionResult<T>> {
    setIsPending(true);
    setErrorMessage(null);
    try {
      return { ok: true, value: await action() };
    } catch (error) {
      setErrorMessage(toErrorMessage(error));
      return { ok: false };
    } finally {
      setIsPending(false);
    }
  }

  return {
    isPending,
    errorMessage,
    run,
    clearError: () => setErrorMessage(null),
  };
}
