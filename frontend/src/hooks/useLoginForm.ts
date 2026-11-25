import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { login } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import type { LoginCredentials } from "@/types/auth";

import { useAsyncAction } from "./useAsyncAction";

const UNAUTHORIZED_STATUS = 401;
const INVALID_CREDENTIALS_MESSAGE = "帳號或密碼錯誤";

/** 呼叫登入 API；帳密錯誤（401）一律顯示固定訊息，其他錯誤沿用 `toErrorMessage()`。 */
async function loginWithMessage(credentials: LoginCredentials) {
  try {
    return await login(credentials);
  } catch (error) {
    if (error instanceof ApiError && error.status === UNAUTHORIZED_STATUS) {
      throw new ApiError(UNAUTHORIZED_STATUS, INVALID_CREDENTIALS_MESSAGE);
    }
    throw error;
  }
}

/** 登入表單狀態：送出中停用按鈕、失敗時保留錯誤訊息，成功後回到 `nextPath`。 */
export function useLoginForm(nextPath: string) {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const action = useAsyncAction();
  const canSubmit = username !== "" && password !== "" && !action.isPending;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    const result = await action.run(() =>
      loginWithMessage({ username, password }),
    );
    if (result.ok) {
      router.replace(nextPath);
      router.refresh();
    }
  }

  const { isPending, errorMessage } = action;
  return {
    username,
    setUsername,
    password,
    setPassword,
    isPending,
    errorMessage,
    canSubmit,
    submit,
  };
}
