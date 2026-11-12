import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { pollUntilAborted } from "./pollLoop";

describe("pollUntilAborted", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("前一次未完成時不會發出下一次請求", async () => {
    const controller = new AbortController();
    let release: () => void = () => {};
    const poll = vi.fn(
      () => new Promise<void>((resolve) => (release = resolve)),
    );
    void pollUntilAborted(poll, 1000, controller.signal);

    await vi.advanceTimersByTimeAsync(1000);
    await vi.advanceTimersByTimeAsync(5000);
    expect(poll).toHaveBeenCalledTimes(1);

    release();
    await vi.advanceTimersByTimeAsync(1000);
    expect(poll).toHaveBeenCalledTimes(2);
    controller.abort();
  });

  it("中止後不再發出請求，也不留下計時器", async () => {
    const controller = new AbortController();
    const poll = vi.fn(async () => {});
    const finished = pollUntilAborted(poll, 1000, controller.signal);

    controller.abort();
    await finished;
    await vi.advanceTimersByTimeAsync(5000);

    expect(poll).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });
});
