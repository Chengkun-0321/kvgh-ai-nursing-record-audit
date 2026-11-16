// @vitest-environment jsdom
import { act } from "react";
import { beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import {
  type AuditRuleStatus,
  type AuditRun,
  getPatientAuditDay,
  type PatientAuditDay,
  runPatientAudit,
} from "@/lib/api/patientAudits";

import { useAuditRuns } from "./useAuditRuns";
import { renderHookHarness } from "./useAuditRunsHarness";

vi.mock("@/lib/api/patientAudits", () => ({
  runPatientAudit: vi.fn(),
  getPatientAuditDay: vi.fn(),
}));

const runPatientAuditMock = vi.mocked(runPatientAudit);
const getPatientAuditDayMock = vi.mocked(getPatientAuditDay);

function makeRun(ruleCode: string, businessDate: string): AuditRun {
  return {
    id: `${ruleCode}-${businessDate}`,
    rule_code: ruleCode,
    rule_name: `規則 ${ruleCode}`,
    patient_key: "P001",
    business_date: businessDate,
    status: "COMPLETED",
    status_label: "已完成",
    status_reason: null,
    verdict: "PASS",
    verdict_label: "紀錄完整",
    summary: `${ruleCode} 結果`,
    findings: [],
    details: null,
    model: "test-model",
    prompt_version: 1,
    system_prompt_version: 1,
    duration_ms: 10,
    created_at: "2026-11-16T00:00:00Z",
  };
}

function makeRule(
  ruleCode: string,
  overrides: Partial<AuditRuleStatus> = {},
): AuditRuleStatus {
  return {
    rule_code: ruleCode,
    name: `規則 ${ruleCode}`,
    description: "",
    cycle: "daily",
    cycle_label: "每日",
    effective_business_date: "2026-11-16",
    availability: { state: "available", label: "可執行", reason: null },
    can_run: true,
    include_in_run_all: true,
    latest_run: null,
    ...overrides,
  };
}

function makeDay(
  businessDate: string,
  rules: AuditRuleStatus[],
): PatientAuditDay {
  return {
    patient_key: "P001",
    ward_code: "W63",
    bed_code: "01",
    admitted_at: null,
    admitted_at_text: null,
    business_date: businessDate,
    available_dates: [businessDate],
    previous_date: null,
    next_date: null,
    rules,
  };
}

function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve: (value: T) => void = () => {};
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => {
  runPatientAuditMock.mockReset();
  getPatientAuditDayMock.mockReset();
  // 預設重新讀取失敗，讓既有測試只依本地執行狀態判斷
  getPatientAuditDayMock.mockRejectedValue(new Error("未設定"));
});

it("一次性規則執行成功後重新讀取總覽，can_run 變為 false 且不再可一鍵稽核", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [makeRule("R01", { can_run: true })]),
  );
  runPatientAuditMock.mockResolvedValue(makeRun("R01", "2026-11-16"));
  getPatientAuditDayMock.mockResolvedValue(
    makeDay("2026-11-16", [
      makeRule("R01", {
        can_run: false,
        include_in_run_all: false,
        latest_run: makeRun("R01", "2026-11-16"),
      }),
    ]),
  );

  await act(() => harness.current.runRule("R01"));
  await act(() => Promise.resolve());

  expect(getPatientAuditDayMock).toHaveBeenCalledWith(
    "P001",
    "2026-11-16",
    expect.any(AbortSignal),
  );
  expect(harness.current.rules[0]?.can_run).toBe(false);
  expect(harness.current.canRunAll).toBe(false);
  expect(harness.current.rules[0]?.displayedRun?.summary).toBe("R01 結果");
});

it("切走再切回原日期後，使用伺服器新載入的規則，不採用舊的總覽快照", async () => {
  const day1105 = makeDay("2026-11-05", [makeRule("R01", { can_run: true })]);
  const day1104 = makeDay("2026-11-04", [makeRule("R01", { can_run: true })]);
  const harness = await renderHookHarness(useAuditRuns, day1105);
  runPatientAuditMock.mockResolvedValue(makeRun("R01", "2026-11-05"));
  getPatientAuditDayMock.mockResolvedValue(
    makeDay("2026-11-05", [makeRule("R01", { can_run: false })]),
  );

  await act(() => harness.current.runRule("R01"));
  await act(() => Promise.resolve());
  expect(harness.current.rules[0]?.can_run).toBe(false);

  await act(() => harness.rerender(day1104));
  // 伺服器重新載入的 11/05：規則已是可執行，與先前快照不同
  const reloaded1105 = makeDay("2026-11-05", [
    makeRule("R01", { can_run: true }),
  ]);
  await act(() => harness.rerender(reloaded1105));

  expect(harness.current.rules[0]?.can_run).toBe(true);
  expect(harness.current.canRunAll).toBe(true);
});

it("重新讀取總覽失敗時保留目前畫面，不清除執行結果", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [makeRule("R01")]),
  );
  runPatientAuditMock.mockResolvedValue(makeRun("R01", "2026-11-16"));

  await act(() => harness.current.runRule("R01"));
  await act(() => Promise.resolve());

  expect(harness.current.rules[0]?.can_run).toBe(true);
  expect(harness.current.rules[0]?.displayedRun?.summary).toBe("R01 結果");
});

it("單項執行成功後，顯示的結果換成新結果", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [makeRule("R01")]),
  );
  runPatientAuditMock.mockResolvedValue(makeRun("R01", "2026-11-16"));

  await act(() => harness.current.runRule("R01"));

  const view = harness.current.rules[0];
  expect(view?.displayedRun?.summary).toBe("R01 結果");
  expect(view?.isRunning).toBe(false);
  expect(view?.errorMessage).toBeNull();
});

it("單項失敗只影響該項的錯誤訊息，其他項不受影響", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [makeRule("R01"), makeRule("R02")]),
  );
  runPatientAuditMock.mockImplementation(async ({ ruleCode }) => {
    if (ruleCode === "R01") {
      throw new ApiError(409, "尚未設定使用中的模型");
    }
    return makeRun(ruleCode, "2026-11-16");
  });

  await act(() => harness.current.runRule("R01"));
  await act(() => harness.current.runRule("R02"));

  const [failed, succeeded] = harness.current.rules;
  expect(failed?.errorMessage).toBe("尚未設定使用中的模型");
  expect(failed?.displayedRun).toBeNull();
  expect(succeeded?.errorMessage).toBeNull();
  expect(succeeded?.displayedRun?.rule_code).toBe("R02");
});

it("一鍵稽核只送出 include_in_run_all 且可執行的項目", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [
      makeRule("R01"),
      makeRule("R02", { can_run: false }),
      makeRule("R03", { include_in_run_all: false }),
      makeRule("R04"),
    ]),
  );
  runPatientAuditMock.mockImplementation(async ({ ruleCode }) =>
    makeRun(ruleCode, "2026-11-16"),
  );

  expect(harness.current.canRunAll).toBe(true);
  await act(() => harness.current.runAll());

  const codes = runPatientAuditMock.mock.calls.map(([input]) => input.ruleCode);
  expect(codes.sort()).toEqual(["R01", "R04"]);
  expect(harness.current.isRunningAll).toBe(false);
});

it("沒有可一鍵稽核的項目時 canRunAll 為 false", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [makeRule("R01", { can_run: false })]),
  );

  expect(harness.current.canRunAll).toBe(false);
});

it("一鍵稽核進行中 isRunningAll 為 true，全部完成後為 false", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [makeRule("R01")]),
  );
  const pending = deferred<AuditRun>();
  runPatientAuditMock.mockReturnValueOnce(pending.promise);

  let running: Promise<void> = Promise.resolve();
  await act(() => {
    running = harness.current.runAll();
  });
  expect(harness.current.isRunningAll).toBe(true);

  await act(async () => {
    pending.resolve(makeRun("R01", "2026-11-16"));
    await running;
  });
  expect(harness.current.isRunningAll).toBe(false);
});

it("切換日期後，舊日期的遲到回應被丟棄，且舊請求被中止", async () => {
  const dayA = makeDay("2026-11-16", [makeRule("R01")]);
  const dayB = makeDay("2026-11-17", [makeRule("R01")]);
  const harness = await renderHookHarness(useAuditRuns, dayA);
  const pending = deferred<AuditRun>();
  runPatientAuditMock.mockReturnValueOnce(pending.promise);

  let running: Promise<void> = Promise.resolve();
  await act(() => {
    running = harness.current.runRule("R01");
  });
  await act(() => harness.rerender(dayB));
  const signal = runPatientAuditMock.mock.calls[0]?.[1];
  expect(signal?.aborted).toBe(true);
  expect(harness.current.rules[0]?.isRunning).toBe(false);

  await act(async () => {
    pending.resolve(makeRun("R01", "2026-11-16"));
    await running;
  });
  expect(harness.current.rules[0]?.displayedRun).toBeNull();
  expect(harness.current.rules[0]?.isRunning).toBe(false);
});

it("切回原日期時，執行中旗標不會殘留", async () => {
  const dayA = makeDay("2026-11-16", [makeRule("R01")]);
  const dayB = makeDay("2026-11-17", [makeRule("R01")]);
  const harness = await renderHookHarness(useAuditRuns, dayA);
  runPatientAuditMock.mockReturnValueOnce(deferred<AuditRun>().promise);

  await act(() => {
    void harness.current.runRule("R01");
  });
  await act(() => harness.rerender(dayB));
  await act(() => harness.rerender(dayA));

  expect(harness.current.rules[0]?.isRunning).toBe(false);
  expect(harness.current.isRunningAll).toBe(false);
});

it("卸載元件時中止執行中的請求", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [makeRule("R01")]),
  );
  runPatientAuditMock.mockReturnValueOnce(deferred<AuditRun>().promise);

  await act(() => {
    void harness.current.runRule("R01");
  });
  await act(() => harness.unmount());

  expect(runPatientAuditMock.mock.calls[0]?.[1]?.aborted).toBe(true);
});

it("執行中再次觸發同一項，不會重複送出", async () => {
  const harness = await renderHookHarness(
    useAuditRuns,
    makeDay("2026-11-16", [makeRule("R01")]),
  );
  const pending = deferred<AuditRun>();
  runPatientAuditMock.mockReturnValueOnce(pending.promise);

  let first: Promise<void> = Promise.resolve();
  let second: Promise<void> = Promise.resolve();
  await act(() => {
    first = harness.current.runRule("R01");
    second = harness.current.runRule("R01");
  });
  await act(async () => {
    pending.resolve(makeRun("R01", "2026-11-16"));
    await Promise.all([first, second]);
  });

  expect(runPatientAuditMock).toHaveBeenCalledTimes(1);
});
