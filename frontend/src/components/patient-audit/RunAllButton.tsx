import { CircleNotchIcon, ListChecksIcon } from "@/components/ui/icons";

type RunAllButtonProps = {
  canRunAll: boolean;
  isRunning: boolean;
  onRunAll: () => void;
};

/** 一鍵稽核：沒有可執行項目時停用；執行中顯示旋轉圖示與進度文字。 */
export function RunAllButton({
  canRunAll,
  isRunning,
  onRunAll,
}: RunAllButtonProps) {
  const label = isRunning
    ? "稽核中…"
    : canRunAll
      ? "一鍵稽核"
      : "目前無可稽核項目";
  return (
    <button
      type="button"
      disabled={!canRunAll || isRunning}
      onClick={onRunAll}
      className="inline-flex min-h-11 pressable items-center gap-2 rounded-full bg-accent px-5 text-body font-semibold whitespace-nowrap text-accent-contrast focus-ring disabled:cursor-not-allowed disabled:opacity-45"
    >
      {isRunning ? (
        <CircleNotchIcon
          aria-hidden="true"
          className="size-4.5 motion-safe:animate-spin"
        />
      ) : (
        <ListChecksIcon aria-hidden="true" className="size-4.5" />
      )}
      {label}
    </button>
  );
}
