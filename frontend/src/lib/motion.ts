import type { Transition } from "motion/react";

// 動態原則見 docs/conventions/ui-design.md「動態」：預設臨界阻尼 spring，
// 只有帶動量的手勢（拖曳放手）才允許回彈；spring 可隨時中斷並從目前位置重新出發

/** 預設 spring：臨界阻尼、不回彈，約 0.35 秒到位（選取框、分段控制器指示器）。 */
export const SPRING_DEFAULT: Transition = {
  type: "spring",
  bounce: 0,
  visualDuration: 0.35,
};

/** Bottom sheet 開關；拖曳放手後的退場沿用目前速度，所以不另設回彈。 */
export const SPRING_SHEET: Transition = {
  type: "spring",
  bounce: 0,
  visualDuration: 0.3,
};

/** Sheet：位移用 spring 並同時淡入，大面積物件在移動初段呈半透明；減少動態時只保留淡入。 */
export const SHEET_TRANSITION: Transition = {
  ...SPRING_SHEET,
  opacity: { duration: 0.2, ease: "easeOut" },
};

/** 內容切換：只淡入，不位移。 */
export const FADE_FAST: Transition = { duration: 0.15, ease: "easeOut" };

/** 遮罩淡入淡出。 */
export const FADE_SCRIM: Transition = { duration: 0.2, ease: "easeOut" };

/** Sheet 往上拖超過邊界時的阻力（橡皮筋）；往下則 1:1 跟手。 */
export const SHEET_DRAG_ELASTIC = { top: 0.06, bottom: 1 } as const;

// Apple〈Designing Fluid Interfaces〉的減速率，與一般捲動手感相同
const DECELERATION_RATE = 0.998;
const SHEET_DISMISS_RATIO = 0.35;

/**
 * 依放手速度推算手勢自然停止的位置（動量投影）。
 *
 * @param velocityPxPerSecond 放手瞬間的速度（px/s）
 * @returns 還會繼續前進的距離（px）
 */
export function projectMomentum(velocityPxPerSecond: number): number {
  return (
    ((velocityPxPerSecond / 1000) * DECELERATION_RATE) / (1 - DECELERATION_RATE)
  );
}

/**
 * 判斷拖曳放手後 sheet 是否該關閉：以投影後的落點判斷，輕甩也能關閉。
 *
 * @param offsetPx 目前往下拖曳的距離
 * @param velocityPxPerSecond 放手速度（往下為正）
 * @param sheetHeightPx sheet 高度
 */
export function shouldDismissSheet(
  offsetPx: number,
  velocityPxPerSecond: number,
  sheetHeightPx: number,
): boolean {
  const projectedPx = offsetPx + projectMomentum(velocityPxPerSecond);
  return projectedPx > sheetHeightPx * SHEET_DISMISS_RATIO;
}
