import { type RefObject, useEffect } from "react";

export type DismissReason = "escape" | "outside";

type DismissableOptions = {
  isActive: boolean;
  containerRef: RefObject<HTMLElement | null>;
  /** 點到符合此選擇器的元素不視為「外部」（例如切換到另一張病床） */
  keepSelector: string;
  /** 需為穩定參考（React Compiler 會自動 memo），避免每次渲染重新訂閱 */
  onDismiss: (reason: DismissReason) => void;
};

/** 判斷指標按下的位置是否在浮層內，或屬於不觸發關閉的元素。 */
function isInsideTarget(
  target: EventTarget | null,
  container: HTMLElement | null,
  keepSelector: string,
): boolean {
  if (!(target instanceof Element)) {
    return false;
  }
  return (
    container?.contains(target) === true ||
    target.closest(keepSelector) !== null
  );
}

/**
 * 非模態浮層的關閉行為：按 Esc，或在浮層與 `keepSelector` 以外的地方按下指標時關閉。
 */
export function useDismissable({
  isActive,
  containerRef,
  keepSelector,
  onDismiss,
}: DismissableOptions): void {
  useEffect(() => {
    if (!isActive) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented) {
        onDismiss("escape");
      }
    };
    const handlePointerDown = (event: PointerEvent) => {
      if (!isInsideTarget(event.target, containerRef.current, keepSelector)) {
        onDismiss("outside");
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("pointerdown", handlePointerDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [isActive, containerRef, keepSelector, onDismiss]);
}
