"use client";

import { useSyncExternalStore } from "react";

import { CLOCK_TICK_MS } from "@/lib/constants";
import { formatDateTime } from "@/lib/format";

type CurrentTimeProps = {
  className?: string;
};

function subscribe(onTick: () => void): () => void {
  const timerId = window.setInterval(onTick, CLOCK_TICK_MS);
  return () => window.clearInterval(timerId);
}

// 同一個 tick 內回傳相同數值，React 才不會重複渲染
function getTickSnapshot(): number {
  return Math.floor(Date.now() / CLOCK_TICK_MS);
}

// 伺服器端不輸出時間，避免與瀏覽器時間不同造成 hydration 不一致
function getServerSnapshot(): null {
  return null;
}

/** 頂列的目前日期時間（Asia/Taipei）。 */
export function CurrentTime({ className }: CurrentTimeProps) {
  const tick = useSyncExternalStore(
    subscribe,
    getTickSnapshot,
    getServerSnapshot,
  );
  if (tick === null) {
    return <span className={className} aria-hidden="true" />;
  }
  const now = new Date(tick * CLOCK_TICK_MS);
  return (
    <time dateTime={now.toISOString()} className={className}>
      {formatDateTime(now)}
    </time>
  );
}
