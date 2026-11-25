import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";

import type { AuditRuleView } from "@/hooks/useAuditRuns";

import { AuditResultBody } from "./AuditResultBody";
import { AuditRuleCard } from "./AuditRuleCard";

it("結果顯示 PASS 發現與後端文字、證據，卡片只顯示整體判定", () => {
  const run: NonNullable<AuditRuleView["displayedRun"]> = {
    id: "run-1",
    rule_code: "R06",
    rule_name: "會診",
    patient_key: "P001",
    business_date: "2026-11-05",
    status: "COMPLETED",
    status_label: "已完成",
    status_reason: null,
    verdict: "PASS",
    verdict_label: "整體完整",
    summary: null,
    findings: [
      {
        position: 1,
        item: "2026-11-05 腸胃科",
        verdict: "PASS",
        verdict_label: "寬限期中",
        message: "追蹤期限至 2026-11-06",
        evidence: [
          {
            source: "consult",
            source_label: "會診紀錄",
            record_id: "record-1",
            field: "內容",
            business_date: "2026-11-05",
            time_text: "2026-11-05 10:00",
            recorded_at: null,
            excerpt: "會診原文",
          },
        ],
      },
    ],
    details: null,
    model: null,
    prompt_version: null,
    system_prompt_version: null,
    duration_ms: null,
    created_at: "2026-11-05T00:00:00Z",
  };
  const rule: AuditRuleView = {
    rule_code: "R06",
    name: "會診",
    description: "",
    cycle: "daily",
    cycle_label: "每日",
    effective_business_date: "2026-11-05",
    availability: { state: "available", label: "可執行", reason: null },
    can_run: true,
    include_in_run_all: true,
    is_running: false,
    latest_run: run,
    displayedRun: run,
    isRunning: false,
    errorMessage: null,
  };

  const result = renderToStaticMarkup(
    <AuditResultBody rule={rule} titleId="title" onClose={() => {}} />,
  );
  for (const value of [
    "寬限期中",
    "2026-11-05 腸胃科",
    "追蹤期限至 2026-11-06",
    "會診紀錄",
    "會診原文",
    "text-verdict-pass-strong",
    "text-verdict-pass",
  ]) {
    expect(result).toContain(value);
  }
  const card = renderToStaticMarkup(
    <AuditRuleCard
      rule={rule}
      pageDate="2026-11-05"
      onOpen={() => {}}
      onRun={() => {}}
    />,
  );
  expect(card).toContain("整體完整");
  expect(card).not.toContain("寬限期中");
  expect(card).not.toContain("腸胃科");
});
