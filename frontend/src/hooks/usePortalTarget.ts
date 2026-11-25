import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** 取得 layout 預留的 portal 插槽；伺服器端與水合前為 null，不渲染 portal 內容。 */
export function usePortalTarget(id: string): HTMLElement | null {
  return useSyncExternalStore(
    subscribe,
    () => document.getElementById(id),
    () => null,
  );
}
