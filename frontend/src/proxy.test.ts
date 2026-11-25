import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "./proxy";

const ORIGIN = "http://localhost:3000";

function request(path: string, hasSession: boolean): NextRequest {
  const headers = hasSession ? { cookie: "kvgh_session=abc" } : undefined;
  return new NextRequest(`${ORIGIN}${path}`, { headers });
}

function location(response: Response): string | null {
  return response.headers.get("location");
}

describe("proxy", () => {
  it("未登入時導向登入頁並帶上原路徑", () => {
    const response = proxy(request("/patients/a?date=2026-01-01", false));
    expect(location(response)).toBe(
      `${ORIGIN}/login?next=%2Fpatients%2Fa%3Fdate%3D2026-01-01`,
    );
  });

  it("未登入造訪登入頁時放行", () => {
    expect(location(proxy(request("/login", false)))).toBeNull();
  });

  it("已登入造訪登入頁時回首頁", () => {
    expect(location(proxy(request("/login?next=%2Fraw-data", true)))).toBe(
      `${ORIGIN}/`,
    );
  });

  it("登入失效時清除 cookie 並去掉 expired", () => {
    const response = proxy(request("/login?next=%2Fraw-data&expired=1", true));
    expect(location(response)).toBe(`${ORIGIN}/login?next=%2Fraw-data`);
    expect(response.headers.get("set-cookie")).toMatch(/^kvgh_session=;/);
  });

  it("已登入時放行並轉送目前路徑", () => {
    const response = proxy(request("/raw-data?patient=x", true));
    expect(location(response)).toBeNull();
    expect(
      response.headers.get("x-middleware-request-x-kvgh-request-path"),
    ).toBe("/raw-data?patient=x");
  });
});
