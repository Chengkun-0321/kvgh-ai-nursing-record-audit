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

/** Server Component 用 `API_BASE_URL`，瀏覽器端用 `NEXT_PUBLIC_API_BASE_URL`（建置時內嵌）。 */
function resolveBaseUrl(): string {
  const baseUrl =
    typeof window === "undefined"
      ? (process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL)
      : process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!baseUrl) {
    throw new ApiError(0, "尚未設定後端位址，請參考 frontend/.env.example");
  }
  return baseUrl;
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
  init: RequestInit = {},
): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${resolveBaseUrl()}${path}`, {
      cache: "no-store",
      ...init,
      headers: { "Content-Type": "application/json", ...init.headers },
    });
  } catch (error) {
    if (isAbortError(error) || error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(0, BACKEND_UNREACHABLE_MESSAGE);
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response;
}

/** 呼叫後端 API 並解析 JSON 回應（型別由 `types/api.ts` 提供）。 */
export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
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
