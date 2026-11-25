import { describe, expect, it } from "vitest";

import { buildLoginPath, sanitizeNextPath } from "./auth";

describe("sanitizeNextPath", () => {
  it.each([
    ["/", "/"],
    ["/patients/abc?date=2026-01-01", "/patients/abc?date=2026-01-01"],
    ["/raw-data#top", "/raw-data#top"],
  ])("接受站內路徑 %s", (raw, expected) => {
    expect(sanitizeNextPath(raw)).toBe(expected);
  });

  it.each([
    null,
    undefined,
    "",
    "//evil.com",
    "///evil.com",
    "/\\evil.com",
    "/\t/evil.com",
    "/\n/evil.com",
    "https://evil.com",
    "javascript:alert(1)",
    "patients",
  ])("拒絕非站內路徑 %j，改回首頁", (raw) => {
    expect(sanitizeNextPath(raw)).toBe("/");
  });
});

describe("buildLoginPath", () => {
  it("首頁不帶 next", () => {
    expect(buildLoginPath("/")).toBe("/login");
  });

  it("帶上原路徑並編碼 query", () => {
    expect(buildLoginPath("/patients/a?date=2026-01-01")).toBe(
      "/login?next=%2Fpatients%2Fa%3Fdate%3D2026-01-01",
    );
  });

  it("登入失效時加上 expired", () => {
    expect(buildLoginPath("/raw-data", true)).toBe(
      "/login?next=%2Fraw-data&expired=1",
    );
  });

  it("外站路徑不會進入 next", () => {
    expect(buildLoginPath("//evil.com")).toBe("/login");
  });
});
