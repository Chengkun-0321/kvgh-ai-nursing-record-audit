"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import {
  isNavItemActive,
  NAV_DISABLED_HINT,
  NAV_ITEMS,
  type NavItemConfig,
} from "./navItems";
import { PendingBadge } from "./PendingBadge";

type MobileTabBarProps = {
  pendingBedCount: number;
};

type TabItemProps = {
  item: NavItemConfig;
  isActive: boolean;
  badgeCount: number;
};

const TAB_CLASS =
  "relative flex min-h-12 flex-col items-center justify-center gap-0.5 text-tab whitespace-nowrap";

function TabItem({ item, isActive, badgeCount }: TabItemProps) {
  const Icon = item.icon;
  const content = (
    <>
      <Icon
        weight={isActive ? "fill" : "regular"}
        aria-hidden="true"
        className="size-6"
      />
      {item.label}
      <PendingBadge
        count={badgeCount}
        className="absolute top-1 left-1/2 ml-2"
      />
    </>
  );

  if (item.href === null) {
    return (
      <span
        aria-disabled="true"
        title={`${item.label}（${NAV_DISABLED_HINT}）`}
        className={cn(TAB_CLASS, "text-ink/35")}
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
        "pressable rounded-xl focus-ring",
        isActive ? "font-semibold text-ink" : "text-ink-secondary",
      )}
    >
      {content}
    </Link>
  );
}

/** 手機／平板的底部分頁列（最多 5 項），避開 iOS 底部安全區域。 */
export function MobileTabBar({ pendingBedCount }: MobileTabBarProps) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="主要導覽"
      className="glass fixed inset-x-0 bottom-0 z-30 pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <ul className="grid grid-cols-5 px-2 pt-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.label}>
            <TabItem
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
