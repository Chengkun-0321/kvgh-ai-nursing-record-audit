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

/** 從緩衝區切出完整的事件區塊，回傳區塊與剩下未完成的部分。 */
export function splitSseBuffer(buffer: string): {
  blocks: string[];
  rest: string;
} {
  const parts = buffer.replace(/\r\n?/g, "\n").split(EVENT_SEPARATOR);
  return { blocks: parts.slice(0, -1), rest: parts.at(-1) ?? "" };
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
  while (!isDone) {
    const chunk = await reader.read();
    isDone = chunk.done;
    // stream 模式保留被切斷的多位元組字元（中文），結束時再一次輸出
    const text = decoder.decode(chunk.value, { stream: !isDone });
    const { blocks, rest } = splitSseBuffer(buffer + text);
    buffer = rest;
    yield* dataFromBlocks(isDone ? [...blocks, rest] : blocks);
  }
}
