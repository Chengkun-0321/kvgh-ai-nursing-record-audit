/** 等待指定毫秒；中止時提前結束（不拋錯）並清除計時器。 */
function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", done);
      resolve();
    };
    const timer = setTimeout(done, ms);
    signal.addEventListener("abort", done);
  });
}

/**
 * 循序輪詢：前一次 `poll` 完成後才等待間隔並排下一次，因此請求不會重疊；
 * `signal` 中止後不再發出新的 `poll`。`poll` 須自行處理錯誤。
 *
 * @param poll 每輪執行的工作，會收到同一個 `signal`
 * @param intervalMs 上一次完成到下一次開始的間隔（毫秒）
 */
export async function pollUntilAborted(
  poll: () => Promise<void>,
  intervalMs: number,
  signal: AbortSignal,
): Promise<void> {
  while (!signal.aborted) {
    await delay(intervalMs, signal);
    if (!signal.aborted) {
      await poll();
    }
  }
}
