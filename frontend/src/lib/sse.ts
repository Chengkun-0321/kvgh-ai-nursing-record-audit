// SSE 事件以空行分隔；統一換行字元後再切割
const EVENT_SEPARATOR = "\n\n";
const DATA_FIELD = "data:";

/**
 * 取出一個 SSE 事件區塊的 data 內容；多行 data 以換行合併，註解行（`:` 開頭）與其他欄位忽略。
 *
 * @returns data 內容；區塊沒有 data 時為 `null`（例如 keep-alive 註解）
 */
export function parseSseBlock(block: string): string | null {
  const dataLines = block
    .split("\n")
    .filter((line) => line.startsWith(DATA_FIELD))
    .map((line) => line.slice(DATA_FIELD.length).replace(/^ /, ""));
  return dataLines.length > 0 ? dataLines.join("\n") : null;
}

/**
 * 從緩衝區切出完整的事件區塊，回傳區塊與剩下未完成的部分。
 * 尾端的 `\r` 可能是 `\r\n` 被切開的前半，除非 `flush` 為真（串流已結束），
 * 否則保留在 `rest` 等下一段再判斷，避免誤把 `\r` 與後面的 `\n` 當成兩個換行。
 */
export function splitSseBuffer(
  buffer: string,
  flush = false,
): {
  blocks: string[];
  rest: string;
} {
  const hasPendingCr = !flush && buffer.endsWith("\r");
  const settled = hasPendingCr ? buffer.slice(0, -1) : buffer;
  const parts = settled.replace(/\r\n?/g, "\n").split(EVENT_SEPARATOR);
  const rest = (parts.at(-1) ?? "") + (hasPendingCr ? "\r" : "");
  return { blocks: parts.slice(0, -1), rest };
}

function* dataFromBlocks(blocks: string[]): Generator<string> {
  for (const block of blocks) {
    const data = parseSseBlock(block);
    if (data !== null) {
      yield data;
    }
  }
}

/**
 * 將 SSE 位元組串流逐一解析為各事件的 data 字串；串流結束時一併處理最後未以空行結尾的區塊。
 * 呼叫端提早離開（break、例外、中止）時會取消並釋放 reader，`body` 不會殘留鎖定。
 *
 * @param body `fetch` 回應的 body
 */
export async function* readSseData(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let isDone = false;
  try {
    while (!isDone) {
      const chunk = await reader.read();
      isDone = chunk.done;
      // stream 模式保留被切斷的多位元組字元（中文），結束時再一次輸出
      const text = decoder.decode(chunk.value, { stream: !isDone });
      const { blocks, rest } = splitSseBuffer(buffer + text, isDone);
      buffer = rest;
      yield* dataFromBlocks(isDone ? [...blocks, rest] : blocks);
    }
  } finally {
    await releaseReader(reader);
  }
}

/** 取消並釋放 reader；串流已出錯或已中止時 `cancel` 會拒絕，此時不再拋出額外錯誤。 */
async function releaseReader(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): Promise<void> {
  try {
    await reader.cancel();
  } catch {
    // 串流已因錯誤或中止而結束，原始錯誤由呼叫端處理
  }
  reader.releaseLock();
}
