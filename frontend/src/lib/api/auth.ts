import type { AuthSession, LoginCredentials } from "@/types/auth";

import { ApiError, apiJson, apiRequest } from "./client";

const BASE_PATH = "/api/v1/auth";
const UNAUTHORIZED_STATUS = 401;

/**
 * 以帳密登入；成功時後端以 Set-Cookie 設定登入 cookie。
 * 帳密錯誤的 401 不導向登入頁，交由呼叫端（登入頁）顯示錯誤。
 */
export function login(credentials: LoginCredentials): Promise<AuthSession> {
  return apiJson<AuthSession>(`${BASE_PATH}/login`, {
    method: "POST",
    body: JSON.stringify(credentials),
    redirectOnUnauthorized: false,
  });
}

/** 登出並清除登入 cookie；已失效（401）時同樣視為已登出，由呼叫端導向登入頁。 */
export async function logout(): Promise<void> {
  try {
    await apiRequest(`${BASE_PATH}/logout`, {
      method: "POST",
      redirectOnUnauthorized: false,
    });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === UNAUTHORIZED_STATUS)) {
      throw error;
    }
  }
}

/** 目前登入的帳號；未登入時由 `apiRequest` 導向登入頁。 */
export function getSession(): Promise<AuthSession> {
  return apiJson<AuthSession>(`${BASE_PATH}/session`);
}
