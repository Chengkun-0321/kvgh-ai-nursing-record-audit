// 按鈕與輸入框樣式：整個設定頁不使用白字，主要操作為「淺藍底＋深藍字」（見 ui-design.md「元件模式」）
const BUTTON_BASE =
  "inline-flex min-h-11 shrink-0 pressable items-center justify-center gap-1.5 rounded-full px-4 text-body font-semibold whitespace-nowrap focus-ring disabled:cursor-not-allowed disabled:opacity-45";

/** 主要操作：新增、儲存、送出。 */
export const BUTTON_PRIMARY = `${BUTTON_BASE} bg-accent-tint text-accent-strong hover:bg-accent-tint-strong`;

/** 次要操作：取消、停止、登出。 */
export const BUTTON_SECONDARY = `${BUTTON_BASE} bg-fill text-ink hover:bg-fill-strong`;

/** 破壞性操作：刪除。 */
export const BUTTON_DANGER = `${BUTTON_BASE} bg-danger-tint text-danger hover:bg-danger/15`;

/** 輸入框：白底、外框 ≥3:1，焦點時以操作藍外框標示；錯誤時外框改為紅色。 */
export const INPUT_CLASS =
  "min-h-11 w-full rounded-xl border border-field-border bg-surface px-3.5 text-body text-ink placeholder:text-ink-secondary focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-accent aria-invalid:border-danger";
