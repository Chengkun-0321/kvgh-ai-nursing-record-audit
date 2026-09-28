import type { components } from "@/types/api";

import { apiJson } from "./client";

export type ChatgptAuthStatus = components["schemas"]["ChatgptAuthStatusRead"];

const BASE_PATH = "/api/v1/chatgpt-auth";

/** 取得 ChatGPT 訂閱登入狀態。 */
export function getChatgptAuthStatus(): Promise<ChatgptAuthStatus> {
  return apiJson<ChatgptAuthStatus>(BASE_PATH);
}

/** 開始裝置碼登入，回傳要在 OpenAI 頁面輸入的驗證碼。 */
export function startChatgptLogin(): Promise<ChatgptAuthStatus> {
  return apiJson<ChatgptAuthStatus>(`${BASE_PATH}/device-code`, {
    method: "POST",
  });
}

/** 登出 ChatGPT（刪除後端保存的 token）。 */
export function signOutChatgpt(): Promise<ChatgptAuthStatus> {
  return apiJson<ChatgptAuthStatus>(BASE_PATH, { method: "DELETE" });
}
