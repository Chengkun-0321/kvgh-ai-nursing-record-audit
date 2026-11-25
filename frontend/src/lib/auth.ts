// demo 登入的共用常數與網址處理；proxy、API client、登入頁共用，不可引用 next/headers 等伺服器專用模組

/** 後端設定的登入 cookie（HttpOnly，前端 JS 讀不到內容，只在伺服器端檢查是否存在）。 */
export const SESSION_COOKIE_NAME = "kvgh_session";

export const LOGIN_PATH = "/login";
export const HOME_PATH = "/";

/** 登入後要回到的站內路徑。 */
export const NEXT_PARAM = "next";

/**
 * 帶 cookie 卻被後端回 401（登入已失效）時加上的參數：
 * proxy 看到後清掉失效的 cookie，避免「登入頁 → 首頁 → 登入頁」來回導向。
 */
export const EXPIRED_PARAM = "expired";

/** proxy 轉給 Server Component 的目前路徑（含 query），供 401 導向登入頁時帶上 `next`。 */
export const REQUEST_PATH_HEADER = "x-kvgh-request-path";

// 只用來判斷解析後是否仍在同一來源，不會真的連線
const SAME_ORIGIN_PROBE = "http://same-origin.invalid";

/**
 * 只接受以單一 `/` 開頭的站內路徑，其餘（`//evil.com`、`/\evil.com`、`https://…`、空值）一律回 `/`，
 * 防止登入後被導向外站（open redirect）。
 */
export function sanitizeNextPath(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) {
    return HOME_PATH;
  }
  if (raw.startsWith("/\\")) {
    return HOME_PATH;
  }
  // 瀏覽器解析網址時會刪除 tab／換行，`/\t/evil.com` 會變成 `//evil.com`：以 URL 解析結果再確認一次
  try {
    const parsed = new URL(raw, SAME_ORIGIN_PROBE);
    return parsed.origin === SAME_ORIGIN_PROBE ? raw : HOME_PATH;
  } catch {
    return HOME_PATH;
  }
}

/** 登入頁網址；`next` 經 `sanitizeNextPath`，`isExpired` 表示登入已失效、需清掉 cookie。 */
export function buildLoginPath(next: string, isExpired = false): string {
  const params = new URLSearchParams();
  const safeNext = sanitizeNextPath(next);
  if (safeNext !== HOME_PATH) {
    params.set(NEXT_PARAM, safeNext);
  }
  if (isExpired) {
    params.set(EXPIRED_PARAM, "1");
  }
  const query = params.toString();
  return query ? `${LOGIN_PATH}?${query}` : LOGIN_PATH;
}
