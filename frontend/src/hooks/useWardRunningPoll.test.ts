// @vitest-environment jsdom
import { act } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { makeBed, makeBoard } from "@/components/bed-board/wardBoardFixtures";
import { AUDIT_RUNNING_POLL_MS } from "@/lib/constants";

import { renderHookHarness } from "./useAuditRunsHarness";
import { useWardRunningPoll } from "./useWardRunningPoll";

const { refresh, router } = vi.hoisted(() => {
  const refresh = vi.fn();
  return { refresh, router: { refresh } };
});
vi.mock("next/navigation", () => ({ useRouter: () => router }));

beforeEach(() => {
  vi.useFakeTimers();
  refresh.mockClear();
});
afterEach(() => vi.useRealTimers());

async function tick(times = 1) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(AUDIT_RUNNING_POLL_MS * times);
  });
}

function runningBoard() {
  const bed = makeBed();
  bed.rule_cells[0] = {
    rule_code: "R01",
    state: "RUNNING",
    label: "稽核中",
    verdict: null,
    finding_count: 0,
  };
  return makeBoard([bed]);
}

it("沒有執行中格子時不刷新", async () => {
  const harness = await renderHookHarness(useWardRunningPoll, makeBoard());
  await tick(3);
  expect(refresh).not.toHaveBeenCalled();
  await harness.unmount();
});

it("有格子執行中時每隔指定時間刷新，完成後停止", async () => {
  const harness = await renderHookHarness(useWardRunningPoll, runningBoard());
  expect(refresh).not.toHaveBeenCalled();
  await tick(2);
  expect(refresh).toHaveBeenCalledTimes(2);

  await harness.rerender(makeBoard());
  await tick(3);
  expect(refresh).toHaveBeenCalledTimes(2);
  await harness.unmount();
});

it("切換日期或病房會重新計時，卸載後停止", async () => {
  const harness = await renderHookHarness(useWardRunningPoll, runningBoard());
  await tick();
  const changed = {
    ...runningBoard(),
    ward_code: "W99",
    business_date: "2026-01-05",
  };
  await harness.rerender(changed);
  await tick();
  expect(refresh).toHaveBeenCalledTimes(2);

  await harness.unmount();
  await tick(3);
  expect(refresh).toHaveBeenCalledTimes(2);
});
