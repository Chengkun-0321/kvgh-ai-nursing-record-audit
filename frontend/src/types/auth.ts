import type { components } from "@/types/api";

/** `POST /api/v1/auth/login` 與 `GET /api/v1/auth/session` 的回應：目前登入的帳號。 */
export type AuthSession = components["schemas"]["SessionRead"];

/** `POST /api/v1/auth/login` 的請求內容。 */
export type LoginCredentials = components["schemas"]["LoginRequest"];
