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
const SPRING_SHEET: Transition = {
  type: "spring",
  bounce: 0,
  visualDuration: 0.3,
};

/** Sheet：位移用 spring 並同時淡入，大面積物件在移動初段呈半透明；減少動態時只保留淡入。 */
export const SHEET_TRANSITION: Transition = {
  ...SPRING_SHEET,
  opacity: { duration: 0.2, ease: "easeOut" },
};

/** 詳情大卡：位移與縮放用 spring，透明度另以短淡入，讓玻璃像實體「浮現」而非單純淡入。 */
export const PANEL_TRANSITION: Transition = {
  ...SPRING_DEFAULT,
  opacity: { duration: 0.2, ease: "easeOut" },
};

/** 詳情大卡從右側滑入並微微放大到位，退場反向；減少動態時只保留淡入淡出。 */
export const PANEL_MOTION = {
  initial: { opacity: 0, x: 32, scale: 0.96 },
  animate: { opacity: 1, x: 0, scale: 1 },
  exit: { opacity: 0, x: 32, scale: 0.96 },
} as const;

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
function projectMomentum(velocityPxPerSecond: number): number {
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

/** 篩選時病床淡化：3D 去背圖與 DOM 標籤使用相同時間，兩者同步變淡。 */
export const BED_DIM_TRANSITION: Transition = {
  duration: 0.3,
  ease: "easeOut",
};

/** 被篩選排除的病床不透明度（與 Tailwind `opacity-35` 相同）。 */
export const DIMMED_BED_OPACITY = 0.35;

/** 逐步工作表：由下方微微浮現並放大到位，退場反向；減少動態時只保留淡入淡出。 */
export const WIZARD_SHEET_MOTION = {
  initial: { opacity: 0, y: 24, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: 24, scale: 0.98 },
} as const;

/** 換步驟時內容水平位移的距離：前進由右側進入、返回由左側進入。 */
export const WIZARD_STEP_OFFSET_PX = 24;

/** 換步驟：位移用 spring，透明度另以短淡入。 */
export const WIZARD_STEP_TRANSITION: Transition = {
  ...SPRING_DEFAULT,
  opacity: { duration: 0.15, ease: "easeOut" },
};
