"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { cn } from "@/lib/utils";

import {
  isNavItemActive,
  NAV_DISABLED_HINT,
  NAV_ITEMS,
  type NavItemConfig,
} from "./navItems";
import { PendingBadge } from "./PendingBadge";

type MainNavTabsProps = {
  pendingBedCount: number;
};

type NavTabProps = {
  item: NavItemConfig;
  isActive: boolean;
  badgeCount: number;
};

// 導覽列不隨換頁重新掛載，選取底色因此能以 spring 從上一頁滑到下一頁
const INDICATOR_LAYOUT_ID = "main-nav-indicator";

const TAB_CLASS =
  "relative flex min-h-11 items-center gap-2 rounded-full px-4 text-body whitespace-nowrap";

function NavTab({ item, isActive, badgeCount }: NavTabProps) {
  const Icon = item.icon;
  const content = (
    <>
      {isActive && (
        <SelectionIndicator
          layoutId={INDICATOR_LAYOUT_ID}
          className="rounded-full bg-surface shadow-card"
        />
      )}
      <Icon
        weight={isActive ? "fill" : "regular"}
        aria-hidden="true"
        className={cn("relative size-5 shrink-0", isActive && "text-accent")}
      />
      <span className="relative">{item.label}</span>
      {item.href === null && (
        <span className="sr-only">（{NAV_DISABLED_HINT}）</span>
      )}
      <PendingBadge count={badgeCount} className="relative" />
    </>
  );

  if (item.href === null) {
    return (
      <span
        aria-disabled="true"
        title={`${item.label}（${NAV_DISABLED_HINT}）`}
        className={cn(TAB_CLASS, "cursor-not-allowed text-ink/40")}
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
        TAB_CLASS,
        "pressable focus-ring",
        isActive ? "font-semibold text-ink" : "hover:bg-fill",
      )}
    >
      {content}
    </Link>
  );
}

/** 桌機頂部導覽中央的玻璃膠囊：目前頁以白色實色膠囊標示，換頁時以 spring 滑動。 */
export function MainNavTabs({ pendingBedCount }: MainNavTabsProps) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="主要導覽"
      className="glass pointer-events-auto relative rounded-full p-1.5 shadow-float"
    >
      <ul className="flex items-center gap-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.label}>
            <NavTab
              item={item}
              isActive={isNavItemActive(item, pathname)}
              badgeCount={item.hasPendingBadge ? pendingBedCount : 0}
            />
          </li>
        ))}
      </ul>
    </nav>
  );
}
