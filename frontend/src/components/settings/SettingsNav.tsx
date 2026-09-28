"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_DISABLED_HINT } from "@/components/app-shell/navItems";
import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { cn } from "@/lib/utils";

import {
  isSettingsNavItemActive,
  SETTINGS_NAV_ITEMS,
  type SettingsNavItemConfig,
} from "./settingsNavItems";

type SettingsNavItemProps = {
  item: SettingsNavItemConfig;
  isActive: boolean;
};

// 設定 layout 不隨換頁重新掛載，選取底色因此能以 spring 在分頁間滑動
const INDICATOR_LAYOUT_ID = "settings-nav-indicator";

const ITEM_CLASS =
  "relative flex min-h-11 shrink-0 items-center gap-2.5 rounded-full py-1 pr-4 pl-1.5 text-body whitespace-nowrap lg:min-h-13 lg:rounded-2xl lg:pr-3";

function SettingsNavItem({ item, isActive }: SettingsNavItemProps) {
  const Icon = item.icon;
  const isDisabled = item.href === null;
  const content = (
    <>
      {isActive && (
        <SelectionIndicator
          layoutId={INDICATOR_LAYOUT_ID}
          className="rounded-full bg-surface shadow-card lg:rounded-2xl"
        />
      )}
      <span
        className={cn(
          "relative grid size-8 shrink-0 place-items-center rounded-full lg:rounded-xl",
          isActive ? "bg-accent text-accent-contrast" : "bg-fill",
        )}
      >
        <Icon
          weight={isActive ? "fill" : "regular"}
          aria-hidden="true"
          className="size-4.5"
        />
      </span>
      <span className="relative lg:flex-1">{item.label}</span>
      {isDisabled && (
        <span className="sr-only text-caption lg:not-sr-only">
          {NAV_DISABLED_HINT}
        </span>
      )}
    </>
  );

  if (item.href === null) {
    return (
      <span
        aria-disabled="true"
        title={`${item.label}（${NAV_DISABLED_HINT}）`}
        className={cn(ITEM_CLASS, "cursor-not-allowed text-ink/40")}
      >
        {content}
      </span>
    );
  }
  return (
    <Link
      href={item.href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        ITEM_CLASS,
        "pressable focus-ring",
        isActive ? "font-semibold text-ink" : "hover:bg-fill",
      )}
    >
      {content}
    </Link>
  );
}

/**
 * 設定分頁導覽：桌機為左側 sticky 直欄，手機為可橫向捲動的膠囊列（同一份 DOM，選取底色才能共用同一個 layoutId）。
 * 未實作的設定頁以停用狀態保留位置，並標示「即將推出」。
 */
export function SettingsNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="設定分頁"
      className="-mx-4 [scrollbar-width:none] overflow-x-auto px-4 lg:sticky lg:top-[calc(var(--spacing-toolbar)+1rem)] lg:mx-0 lg:overflow-visible lg:px-0"
    >
      <ul className="flex gap-1.5 py-1 lg:flex-col lg:py-0">
        {SETTINGS_NAV_ITEMS.map((item) => (
          <li key={item.label} className="shrink-0">
            <SettingsNavItem
              item={item}
              isActive={isSettingsNavItemActive(item, pathname)}
            />
          </li>
        ))}
      </ul>
    </nav>
  );
}
