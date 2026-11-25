// @vitest-environment jsdom
import { act } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { getPatientAuditDay } from "@/lib/api/patientAudits";
import { AUDIT_RUNNING_POLL_MS } from "@/lib/constants";

import { makeDay, makeRule, makeRun } from "./auditRunsFixtures";
import { useAuditRuns } from "./useAuditRuns";
import { renderHookHarness } from "./useAuditRunsHarness";

// 重新整理或切換日期後，本頁不再等待原本的請求；稽核中完全依後端回報，並輪詢到完成
vi.mock("@/lib/api/patientAudits", () => ({
  runPatientAudit: vi.fn(),
  getPatientAuditDay: vi.fn(),
}));

const getPatientAuditDayMock = vi.mocked(getPatientAuditDay);
const DAY = "2026-11-16";
const RUNNING_RULE = makeRule("R01", {
  is_running: true,
  include_in_run_all: false,
});
const DONE_DAY = makeDay(DAY, [
  makeRule("R01", { latest_run: makeRun("R01", DAY) }),
]);

beforeEach(() => {
  vi.useFakeTimers();
  getPatientAuditDayMock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

async function tick(times = 1): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(AUDIT_RUNNING_POLL_MS * times);
  });
}

it("後端回報稽核中時，未送出任何請求也顯示稽核中", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay(DAY, [RUNNING_RULE]),
  );

  expect(harness.current.rules[0]?.isRunning).toBe(true);
  expect(getPatientAuditDayMock).not.toHaveBeenCalled();
});

it("稽核中時定期重新讀取總覽，完成後顯示結果並停止輪詢", async () => {
  getPatientAuditDayMock
    .mockResolvedValueOnce(makeDay(DAY, [RUNNING_RULE]))
    .mockResolvedValue(DONE_DAY);
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay(DAY, [RUNNING_RULE]),
  );

  await tick();
  expect(harness.current.rules[0]?.isRunning).toBe(true);

  await tick();
  expect(harness.current.rules[0]?.isRunning).toBe(false);
  expect(harness.current.rules[0]?.displayedRun?.summary).toBe("R01 結果");

  await tick(3);
  expect(getPatientAuditDayMock).toHaveBeenCalledTimes(2);
});

it("沒有項目稽核中時不輪詢", async () => {
  await renderHookHarness(useAuditRuns, makeDay(DAY, [makeRule("R01")]));

  await tick(3);

  expect(getPatientAuditDayMock).not.toHaveBeenCalled();
});

it("切換到其他日期時停止輪詢原日期", async () => {
  getPatientAuditDayMock.mockResolvedValue(makeDay(DAY, [RUNNING_RULE]));
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay(DAY, [RUNNING_RULE]),
  );

  await harness.rerender(makeDay("2026-11-15", [makeRule("R01")]));
  await tick(3);

  expect(getPatientAuditDayMock).not.toHaveBeenCalled();
});
