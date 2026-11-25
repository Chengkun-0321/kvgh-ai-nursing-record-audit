import { type NextRequest, NextResponse } from "next/server";

import {
  buildLoginPath,
  EXPIRED_PARAM,
  HOME_PATH,
  LOGIN_PATH,
  NEXT_PARAM,
  REQUEST_PATH_HEADER,
  SESSION_COOKIE_NAME,
} from "@/lib/auth";

// Next 用戶端導覽時加在網址上的內部參數，不放進登入後要回到的路徑
const RSC_QUERY_PARAM = "_rsc";

/** 目前請求的站內路徑（含 query）。 */
function requestPath(request: NextRequest): string {
  const url = request.nextUrl.clone();
  url.searchParams.delete(RSC_QUERY_PARAM);
  return `${url.pathname}${url.search}`;
}

function redirectTo(request: NextRequest, path: string): NextResponse {
  return NextResponse.redirect(new URL(path, request.url));
}

/**
 * 登入頁：登入已失效（`expired`）時清掉 cookie 並去掉該參數，避免與首頁來回導向；
 * 已有 cookie 時直接回首頁。
 */
function handleLoginPage(request: NextRequest, hasSession: boolean) {
  const { searchParams } = request.nextUrl;
  if (searchParams.has(EXPIRED_PARAM)) {
    const response = redirectTo(
      request,
      buildLoginPath(searchParams.get(NEXT_PARAM) ?? HOME_PATH),
    );
    response.cookies.delete({ name: SESSION_COOKIE_NAME, path: "/" });
    return response;
  }
  return hasSession ? redirectTo(request, HOME_PATH) : NextResponse.next();
}

/**
 * 登入檢查（只看 cookie 是否存在，真正的驗證在後端）：未登入的頁面請求導向登入頁並帶上原路徑。
 * 已登入時把目前路徑放進請求標頭，供 Server Component 遇到 401 時帶回登入頁。
 */
export function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE_NAME);
  if (request.nextUrl.pathname === LOGIN_PATH) {
    return handleLoginPage(request, hasSession);
  }
  const path = requestPath(request);
  if (!hasSession) {
    return redirectTo(request, buildLoginPath(path));
  }
  const headers = new Headers(request.headers);
  headers.set(REQUEST_PATH_HEADER, path);
  return NextResponse.next({ request: { headers } });
}

export const config = {
  matcher: [
    // 不攔截：後端 API（Docker 由 nginx 轉給後端）、Next 內部檔案、public 靜態資源與一般靜態副檔名
    "/((?!api/|_next/|images/|models/|favicon\\.ico$|robots\\.txt$|sitemap\\.xml$|.*\\.(?:png|jpe?g|gif|webp|svg|ico|glb|gltf|bin|txt|xml|webmanifest)$).*)",
  ],
};
