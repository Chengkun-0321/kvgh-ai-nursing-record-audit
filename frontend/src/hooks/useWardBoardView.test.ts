// @vitest-environment jsdom
import { act } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { WARD_BOARD_VIEW_STORAGE_KEY } from "@/lib/wardBoardView";

import { renderHookHarness } from "./useAuditRunsHarness";
import { useWardBoardView } from "./useWardBoardView";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

it.each([null, "invalid", "list"])("儲存值為 %s 時預設清單", async (value) => {
  if (value) localStorage.setItem(WARD_BOARD_VIEW_STORAGE_KEY, value);
  const harness = await renderHookHarness(useWardBoardView, undefined);

  expect(harness.current.view).toBe("list");

  await harness.unmount();
});

it("還原 3D 偏好，切回清單後儲存並於重新掛載還原", async () => {
  localStorage.setItem(WARD_BOARD_VIEW_STORAGE_KEY, "3d");
  const harness = await renderHookHarness(useWardBoardView, undefined);
  expect(harness.current.view).toBe("3d");

  await act(async () => harness.current.setView("list"));
  expect(harness.current.view).toBe("list");
  expect(localStorage.getItem(WARD_BOARD_VIEW_STORAGE_KEY)).toBe("list");
  await harness.unmount();
  const remounted = await renderHookHarness(useWardBoardView, undefined);
  expect(remounted.current.view).toBe("list");
  await remounted.unmount();
});

it("禁止讀寫 localStorage 時預設清單，仍能在本頁切換", async () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("denied");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("denied");
  });
  const harness = await renderHookHarness(useWardBoardView, undefined);
  expect(harness.current.view).toBe("list");

  await act(async () => harness.current.setView("3d"));
  expect(harness.current.view).toBe("3d");

  await harness.unmount();
});
