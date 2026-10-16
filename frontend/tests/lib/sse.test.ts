import { describe, expect, it } from "vitest";

import { parseSseBlock, readSseData, splitSseBuffer } from "@/lib/sse";

function streamOf(chunks: Uint8Array[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(chunk));
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>): Promise<string[]> {
  const items: string[] = [];
  for await (const data of readSseData(stream)) {
    items.push(data);
  }
  return items;
}

describe("parseSseBlock", () => {
  it("取出 data 內容並忽略註解行", () => {
    expect(parseSseBlock(': ping\ndata: {"type":"delta"}')).toBe(
      '{"type":"delta"}',
    );
  });

  it("沒有 data 的區塊回傳 null", () => {
    expect(parseSseBlock(": ping")).toBeNull();
  });
});

describe("splitSseBuffer", () => {
  it("保留尚未以空行結尾的部分", () => {
    expect(splitSseBuffer("data: a\n\ndata: b")).toEqual({
      blocks: ["data: a"],
      rest: "data: b",
    });
  });
});

describe("readSseData", () => {
  it("中文字被切在兩個 chunk 之間時仍能正確解碼", async () => {
    const bytes = new TextEncoder().encode('data: "你好"\n\ndata: "完成"\n\n');
    const splitAt = 8; // 落在「你」的 UTF-8 位元組中間

    const items = await collect(
      streamOf([bytes.slice(0, splitAt), bytes.slice(splitAt)]),
    );

    expect(items).toEqual(['"你好"', '"完成"']);
  });

  it("串流結束時處理最後沒有空行結尾的事件", async () => {
    const items = await collect(
      streamOf([new TextEncoder().encode("data: last")]),
    );

    expect(items).toEqual(["last"]);
  });
});
