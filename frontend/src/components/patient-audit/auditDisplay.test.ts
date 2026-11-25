import { describe, expect, it } from "vitest";

import type { AuditRuleView } from "@/hooks/useAuditRuns";
import type { AuditAvailability, AuditRun } from "@/lib/api/patientAudits";

import { resolveAuditDisplay } from "./auditDisplay";

function makeView(
  availability: AuditAvailability,
  displayedRun: AuditRun | null = null,
): AuditRuleView {
  return {
    rule_code: "R01",
    name: "規則 R01",
    description: "",
    cycle: "once_per_admission",
    cycle_label: "入院一次",
    effective_business_date: "2026-11-16",
    availability,
    can_run: false,
    include_in_run_all: false,
    is_running: false,
    latest_run: null,
    displayedRun,
    isRunning: false,
    errorMessage: null,
  };
}

describe("resolveAuditDisplay", () => {
  it("day_not_ended 顯示後端給的文字，不落到「尚未稽核」", () => {
    const display = resolveAuditDisplay(
      makeView({
        state: "day_not_ended",
        label: "當日尚未結束",
        reason: "稽核日為今天或之後，需待當日結束後才能稽核",
      }),
    );

    expect(display.kind).toBe("day_not_ended");
    expect(display.label).toBe("當日尚未結束");
    expect(display.reason).toBe("稽核日為今天或之後，需待當日結束後才能稽核");
    expect(display.verdict).toBeNull();
  });

  it("available 且沒有結果時仍顯示「尚未稽核」", () => {
    const display = resolveAuditDisplay(
      makeView({ state: "available", label: "可執行", reason: null }),
    );

    expect(display.kind).toBe("unaudited");
    expect(display.label).toBe("尚未稽核");
  });

  it("data_unavailable 仍顯示為院方尚未提供資料", () => {
    const display = resolveAuditDisplay(
      makeView({
        state: "data_unavailable",
        label: "院方尚未提供資料",
        reason: "缺少轉出摘要",
      }),
    );

    expect(display.kind).toBe("unavailable");
    expect(display.label).toBe("院方尚未提供資料");
  });

  it("入院規則已有完成結果時顯示判定，不看可稽核狀態", () => {
    const run: AuditRun = {
      id: "run-1",
      rule_code: "R01",
      rule_name: "規則 R01",
      patient_key: "P001",
      business_date: "2026-11-16",
      status: "COMPLETED",
      status_label: "已完成",
      status_reason: null,
      verdict: "PASS",
      verdict_label: "紀錄完整",
      summary: "R01 結果",
      findings: [],
      details: null,
      model: "test-model",
      prompt_version: 1,
      system_prompt_version: 1,
      duration_ms: 10,
      created_at: "2026-11-16T00:00:00Z",
    };
    const display = resolveAuditDisplay(
      makeView({ state: "available", label: "可執行", reason: null }, run),
    );

    expect(display.kind).toBe("verdict");
    expect(display.verdict).toBe("PASS");
    expect(display.label).toBe("紀錄完整");
  });
});
