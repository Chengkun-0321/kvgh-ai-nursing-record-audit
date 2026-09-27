"use client";

import { type ReactNode, useDeferredValue } from "react";

/**
 * 子樹改在背景（deferred lane）渲染：載入期間外層已顯示的 Suspense 不切換 fallback，
 * 就緒後立即出現，避開 React 在 fallback 後重新顯示內容時的 300ms 節流。
 * 與渲染器無關，React DOM 與 R3F 場景內都可使用；需放在 Suspense 內。
 */
export function DeferredMount({ children }: { children: ReactNode }) {
  const isMounted = useDeferredValue(true, false);
  return isMounted ? children : null;
}
