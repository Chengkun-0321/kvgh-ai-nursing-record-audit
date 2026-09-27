import { useEffect } from "react";

/**
 * 媒體查詢由不符合變為符合時呼叫 `onMatch`（例如視窗放大到桌機寬度）。
 *
 * @param query CSS 媒體查詢字串
 * @param onMatch 需為穩定參考（以 `useCallback` 包裝），避免每次渲染重新訂閱
 */
export function useOnMediaQueryMatch(query: string, onMatch: () => void): void {
  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const handleChange = (event: MediaQueryListEvent) => {
      if (event.matches) {
        onMatch();
      }
    };
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [query, onMatch]);
}
