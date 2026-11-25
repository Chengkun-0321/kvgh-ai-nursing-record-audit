import {
  buildLoginPath,
  REQUEST_PATH_HEADER,
  SESSION_COOKIE_NAME,
} from "@/lib/auth";

const BACKEND_UNREACHABLE_MESSAGE =
  "無法連線到後端服務，請確認後端已啟動（預設 http://localhost:8000）";

/** 後端回應錯誤；`message` 為可直接顯示的繁中訊息（來自後端 `detail`）。 */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** 回傳 API 基底位址；瀏覽器端的空字串代表同源，伺服器端仍須有後端位址。 */
function resolveBaseUrl(): string {
  const isServer = isServerSide();
  const baseUrl = isServer
    ? (process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL)
    : process.env.NEXT_PUBLIC_API_BASE_URL;
  if (baseUrl === undefined || (isServer && baseUrl === "")) {
    throw new ApiError(0, "尚未設定後端位址，請參考 frontend/.env.example");
  }
  return baseUrl;
}

const UNAUTHORIZED_STATUS = 401;

/** `apiRequest` 的選項；`redirectOnUnauthorized: false` 供登入 API 使用，401 交由登入頁顯示錯誤。 */
export type ApiRequestInit = RequestInit & { redirectOnUnauthorized?: boolean };

function isServerSide(): boolean {
  return typeof window === "undefined";
}

/**
 * 伺服器端（Server Component）呼叫後端時，轉送使用者請求中的登入 cookie。
 * 以動態 import 載入 `next/headers`，瀏覽器端的 bundle 不會靜態引用伺服器專用模組。
 */
async function serverAuthHeaders(): Promise<Record<string, string>> {
  const { cookies } = await import("next/headers");
  const session = (await cookies()).get(SESSION_COOKIE_NAME);
  return session ? { Cookie: `${session.name}=${session.value}` } : {};
}

/**
 * 登入失效（401）時導向登入頁並帶上目前路徑。
 * 伺服器端以 `redirect()` 中止渲染（會拋出 Next 專用例外）；瀏覽器端整頁導向，讓 proxy 清掉失效的 cookie。
 */
async function redirectToLogin(): Promise<void> {
  if (!isServerSide()) {
    const { pathname, search } = window.location;
    window.location.replace(buildLoginPath(`${pathname}${search}`, true));
    return;
  }
  const [{ headers }, { redirect }] = await Promise.all([
    import("next/headers"),
    import("next/navigation"),
  ]);
  const path = (await headers()).get(REQUEST_PATH_HEADER) ?? "/";
  redirect(buildLoginPath(path, true));
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function readErrorDetail(response: Response): Promise<string> {
  const fallback = `後端回應錯誤（HTTP ${response.status}），請稍後再試`;
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      return typeof body.detail === "string" ? body.detail : fallback;
    }
  } catch {
    // 非 JSON 回應（例如 proxy 錯誤頁）：改用通用訊息
  }
  return fallback;
}

/**
 * 呼叫後端 API；網路失敗與非 2xx 回應一律轉為帶繁中訊息的 `ApiError`。
 * 使用者主動中止（AbortController）時照原樣拋出 `AbortError`。
 */
export async function apiRequest(
  path: string,
  { redirectOnUnauthorized = true, ...init }: ApiRequestInit = {},
): Promise<Response> {
  const response = await sendRequest(path, init);
  if (response.status === UNAUTHORIZED_STATUS && redirectOnUnauthorized) {
    await redirectToLogin();
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response;
}

async function sendRequest(path: string, init: RequestInit): Promise<Response> {
  const authHeaders = isServerSide() ? await serverAuthHeaders() : {};
  try {
    return await fetch(`${resolveBaseUrl()}${path}`, {
      cache: "no-store",
      // 本機開發為跨來源（:3000 → :8000），需 include 才會帶上登入 cookie；同源部署亦無影響
      credentials: "include",
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...init.headers,
      },
    });
  } catch (error) {
    if (isAbortError(error) || error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(0, BACKEND_UNREACHABLE_MESSAGE);
  }
}

/** 呼叫後端 API 並解析 JSON 回應（型別由 `types/api.ts` 提供）。 */
export async function apiJson<T>(
  path: string,
  init?: ApiRequestInit,
): Promise<T> {
  const response = await apiRequest(path, init);
  // 回應結構由 FastAPI response_model 保證，與 OpenAPI 產生的型別一致
  return (await response.json()) as T;
}

/** 把任何錯誤轉成可顯示的訊息。 */
export function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "發生未預期的錯誤，請重新整理頁面後再試";
}
