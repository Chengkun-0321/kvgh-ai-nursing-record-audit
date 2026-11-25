import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";

import type { RuleCell, RuleCellState } from "@/lib/api/wards";
import { getRuleCellPresentation } from "@/lib/ruleCellPresentation";

import { RuleCellBadge } from "./RuleCellBadge";

const STATES: RuleCellState[] = [
  "PASS",
  "WARNING",
  "NEEDS_REVIEW",
  "ERROR",
  "RUNNING",
  "FAILED",
  "NOT_APPLICABLE",
  "DATA_UNAVAILABLE",
  "DAY_NOT_ENDED",
  "NOT_AUDITED",
];

it.each(STATES)("%s 一律採後端 label，顯示圖示與文字", (state) => {
  const cell: RuleCell = {
    rule_code: "R01",
    state,
    label: "後端指定文字",
    verdict: null,
    finding_count: 0,
  };
  const html = renderToStaticMarkup(<RuleCellBadge cell={cell} />);
  expect(html).toContain("後端指定文字");
  expect(html).toContain("<svg");
  expect(html).toContain('aria-hidden="true"');
  expect(html.includes("motion-safe:animate-spin")).toBe(state === "RUNNING");
});

it("格子依 state 呈現，忽略不相符的 verdict；數字採後端非 PASS 發現數", () => {
  const cell: RuleCell = {
    rule_code: "R03",
    state: "FAILED",
    label: "執行失敗",
    verdict: "WARNING",
    finding_count: 2,
  };
  expect(getRuleCellPresentation(cell)).toEqual({
    verdict: null,
    text: "執行失敗 2",
    isRunning: false,
  });
  const html = renderToStaticMarkup(<RuleCellBadge cell={cell} />);
  expect(html).toContain("text-ink-secondary");
  expect(html).toContain("執行失敗，2 項發現");
  expect(html).not.toContain("text-verdict-warning");
});

it.each(["PASS", "WARNING", "NEEDS_REVIEW", "ERROR"] as const)(
  "%s 沿用 verdict token 與既有圖示",
  (state) => {
    const cell: RuleCell = {
      rule_code: "R01",
      state,
      label: "後端判定",
      verdict: state,
      finding_count: 0,
    };
    expect(getRuleCellPresentation(cell).verdict).toBe(state);
    expect(renderToStaticMarkup(<RuleCellBadge cell={cell} />)).toContain(
      "text-verdict-",
    );
  },
);
