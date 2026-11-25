import { useId } from "react";
import { createPortal } from "react-dom";

import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { usePortalTarget } from "@/hooks/usePortalTarget";
import { NAV_PAGE_ACTIONS_SLOT_ID } from "@/lib/navSlots";
import { cn } from "@/lib/utils";
import type { WardBoardView } from "@/lib/wardBoardView";

const VIEWS: { value: WardBoardView; label: string }[] = [
  { value: "list", label: "清單" },
  { value: "3d", label: "3D 病房" },
];

/** 「清單／3D 病房」玻璃膠囊；由首頁以 portal 放進頂部導覽，排在使用者狀態左側。 */
export function WardViewToggle({
  value,
  onChange,
}: {
  value: WardBoardView;
  onChange: (view: WardBoardView) => void;
}) {
  const layoutId = useId();
  return (
    <div
      role="group"
      aria-label="病房檢視"
      data-keep-detail
      className="glass flex items-center rounded-full p-1 shadow-float"
    >
      {VIEWS.map((view) => (
        <button
          key={view.value}
          type="button"
          aria-pressed={value === view.value}
          onClick={() => onChange(view.value)}
          className={cn(
            "relative min-h-11 pressable rounded-full px-3 text-footnote font-medium whitespace-nowrap focus-ring lg:px-4",
            value !== view.value && "text-ink-secondary hover:bg-fill",
          )}
        >
          {value === view.value && (
            <SelectionIndicator
              layoutId={layoutId}
              className="rounded-full bg-surface"
            />
          )}
          <span className="relative">{view.label}</span>
        </button>
      ))}
    </div>
  );
}

/** 把檢視切換放進頂部導覽的插槽（桌機導覽或手機頂列）；插槽不存在時不渲染。 */
export function WardViewTogglePortal({
  isDesktop,
  value,
  onChange,
}: {
  isDesktop: boolean;
  value: WardBoardView;
  onChange: (view: WardBoardView) => void;
}) {
  const slot = usePortalTarget(
    NAV_PAGE_ACTIONS_SLOT_ID[isDesktop ? "desktop" : "mobile"],
  );
  return slot
    ? createPortal(<WardViewToggle value={value} onChange={onChange} />, slot)
    : null;
}
