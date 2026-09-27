import { type RefObject, useLayoutEffect } from "react";

type Keyframe = Record<string, string>;

/**
 * 以 Web Animations 寫入地圖元素的位置或 CSS 變數（duration 0、fill forwards），
 * 延續地圖控制器的做法，不使用 React inline style。
 */
export function useMapKeyframe(
  ref: RefObject<HTMLElement | null>,
  keyframe: Keyframe,
) {
  const serialized = JSON.stringify(keyframe);
  useLayoutEffect(() => {
    const frame: Keyframe = JSON.parse(serialized);
    const animation = ref.current?.animate([frame], {
      duration: 0,
      fill: "forwards",
    });
    return () => animation?.cancel();
  }, [ref, serialized]);
}
