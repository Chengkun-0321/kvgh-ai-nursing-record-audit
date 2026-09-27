import { useCallback, useSyncExternalStore } from "react";

// 伺服器端無法得知視窗寬度，一律視為不符合；hydration 後再以實際值更新
function getServerSnapshot(): boolean {
  return false;
}

/**
 * 訂閱 CSS 媒體查詢是否符合（例如是否為桌機寬度）。
 *
 * @param query CSS 媒體查詢字串
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const mediaQuery = window.matchMedia(query);
      mediaQuery.addEventListener("change", onChange);
      return () => mediaQuery.removeEventListener("change", onChange);
    },
    [query],
  );
  const getSnapshot = useCallback(
    () => window.matchMedia(query).matches,
    [query],
  );
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
