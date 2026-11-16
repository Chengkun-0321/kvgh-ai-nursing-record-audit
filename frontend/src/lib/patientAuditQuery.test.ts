import { describe, expect, it } from "vitest";

import { parseAuditDate, patientAuditHref } from "./patientAuditQuery";

describe("parseAuditDate", () => {
  it("採用格式正確的真實日期", () => {
    expect(parseAuditDate("2026-11-16")).toBe("2026-11-16");
    expect(parseAuditDate("2024-02-29")).toBe("2024-02-29");
  });

  it("未指定或空字串時回傳 null", () => {
    expect(parseAuditDate(undefined)).toBeNull();
    expect(parseAuditDate("")).toBeNull();
  });

  it("格式不對時視為未指定", () => {
    expect(parseAuditDate("2026/11/16")).toBeNull();
    expect(parseAuditDate("2026-1-6")).toBeNull();
    expect(parseAuditDate("20261116")).toBeNull();
    expect(parseAuditDate("2026-11-16T00:00")).toBeNull();
  });

  it("不是真實日期時視為未指定", () => {
    expect(parseAuditDate("2026-02-30")).toBeNull();
    expect(parseAuditDate("2026-13-01")).toBeNull();
    expect(parseAuditDate("2025-02-29")).toBeNull();
  });

  it("重複的 query 參數只取第一個", () => {
    expect(parseAuditDate(["2026-11-16", "2026-11-15"])).toBe("2026-11-16");
    expect(parseAuditDate(["bad", "2026-11-15"])).toBeNull();
  });
});

describe("patientAuditHref", () => {
  it("未指定日期時只回傳病患路徑", () => {
    expect(patientAuditHref("P001")).toBe("/patients/P001");
    expect(patientAuditHref("P001", null)).toBe("/patients/P001");
  });

  it("指定有效日期時帶上 date 參數", () => {
    expect(patientAuditHref("P001", "2026-11-16")).toBe(
      "/patients/P001?date=2026-11-16",
    );
  });

  it("無效日期不寫進網址", () => {
    expect(patientAuditHref("P001", "2026-02-30")).toBe("/patients/P001");
    expect(patientAuditHref("P001", "11/16")).toBe("/patients/P001");
  });

  it("病患鍵照原樣編碼", () => {
    expect(patientAuditHref("a b/c?d")).toBe("/patients/a%20b%2Fc%3Fd");
  });
});
