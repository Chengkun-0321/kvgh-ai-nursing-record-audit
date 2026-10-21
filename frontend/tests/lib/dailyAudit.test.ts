import { describe, expect, it } from "vitest";

import {
  auditButtonLabel,
  dayCardState,
  formatBusinessDate,
  formatSimilarity,
  patientAuditPath,
  sortDaysDesc,
  type DayCardState,
} from "@/lib/dailyAudit";
import type { AuditDay } from "@/types/patientAudit";

import {
  DONE_DAY,
  NOT_AUDITABLE_DAY,
  NOT_RUN_DAY,
  makeDay,
  makeSimilarity,
} from "../components/patient-audit/fixtures";

function datesOf(days: AuditDay[]): string[] {
  return days.map((day) => day.business_date);
}

describe("sortDaysDesc", () => {
  it("BR12：依日期由新到舊排列，不修改輸入陣列", () => {
    const input = [
      makeDay("2026-09-01"),
      makeDay("2026-09-04"),
      makeDay("2026-09-02"),
    ];
    const before = datesOf(input);

    const sorted = sortDaysDesc(input);

    expect(datesOf(sorted)).toEqual(["2026-09-04", "2026-09-02", "2026-09-01"]);
    expect(datesOf(input)).toEqual(before);
  });

  it("BR12 邊界：跨月排序（9/30 與 10/01）", () => {
    const input = [makeDay("2026-09-30"), makeDay("2026-10-01")];

    const sorted = sortDaysDesc(input);

    expect(datesOf(sorted)).toEqual(["2026-10-01", "2026-09-30"]);
  });
});

describe("formatBusinessDate", () => {
  it("BR12：日期顯示為 M/D（月不補零、日補零）", () => {
    expect(formatBusinessDate("2026-09-03")).toBe("9/03");
    expect(formatBusinessDate("2026-10-15")).toBe("10/15");
  });
});

describe("formatSimilarity", () => {
  it("BR12：有相似紀錄時的完整文字（加註模型估計）", () => {
    const note = makeSimilarity();

    const text = formatSimilarity(note);

    expect(text).toBe(
      "今日 09:30 紀錄（NPN-B-0904-01）與 9/03 紀錄（NPN-B-0903-01）相似 98.0%（模型估計）",
    );
  });

  it("BR12：recorded_at 以 UTC 表示時仍顯示台北時間 09:30", () => {
    const note = makeSimilarity({ recorded_at: "2026-09-04T01:30:00Z" });

    const text = formatSimilarity(note);

    expect(text).toContain("今日 09:30 紀錄");
  });

  it("BR12：相似度顯示到小數 1 位（97.7 → 97.7%）", () => {
    const text = formatSimilarity(makeSimilarity({ similarity_percent: 97.7 }));

    expect(text).toContain("97.7%");
  });

  it("BR12 邊界：相似度 0 → 0.0%", () => {
    const text = formatSimilarity(makeSimilarity({ similarity_percent: 0 }));

    expect(text).toContain("0.0%");
  });

  it("BR12：沒有相似紀錄時回傳非空字串", () => {
    const note = makeSimilarity({
      similar_record_id: null,
      similar_business_date: null,
      similarity_percent: null,
    });

    const text = formatSimilarity(note);

    expect(text.length).toBeGreaterThan(0);
  });
});

describe("dayCardState", () => {
  const cases: Array<[string, AuditDay, DayCardState]> = [
    ["auditable=false → not_auditable", NOT_AUDITABLE_DAY, "not_auditable"],
    ["可稽核且 latest_finding=null → not_run", NOT_RUN_DAY, "not_run"],
    ["有結果 → done", DONE_DAY, "done"],
  ];

  it.each(cases)("BR13：%s", (_label, day, expected) => {
    expect(dayCardState(day)).toBe(expected);
  });
});

describe("auditButtonLabel", () => {
  const cases: Array<[string, AuditDay, boolean, string | null]> = [
    ["not_auditable、running=false → null", NOT_AUDITABLE_DAY, false, null],
    ["not_auditable、running=true → null", NOT_AUDITABLE_DAY, true, null],
    ["not_run、running=false → 執行稽核", NOT_RUN_DAY, false, "執行稽核"],
    ["done、running=false → 重新稽核", DONE_DAY, false, "重新稽核"],
    ["not_run、running=true → 稽核中…", NOT_RUN_DAY, true, "稽核中…"],
    ["done、running=true → 稽核中…", DONE_DAY, true, "稽核中…"],
  ];

  it.each(cases)("BR13：%s", (_label, day, running, expected) => {
    expect(auditButtonLabel(day, running)).toBe(expected);
  });
});

describe("patientAuditPath", () => {
  it("BR14：路徑為 /patients/ 加上經 URL 編碼的 patient_id", () => {
    expect(patientAuditPath("A病患")).toBe(
      `/patients/${encodeURIComponent("A病患")}`,
    );
    expect(patientAuditPath("P001")).toBe("/patients/P001");
  });
});
