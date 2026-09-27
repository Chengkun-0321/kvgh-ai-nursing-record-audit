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

type AppSidebarProps = {
  pendingBedCount: number;
};

type SidebarItemProps = {
  item: NavItemConfig;
  isActive: boolean;
  badgeCount: number;
};

const ITEM_CLASS =
  "relative flex min-h-14 items-center justify-center gap-3 rounded-xl px-3 text-headline xl:justify-start";

function SidebarItem({ item, isActive, badgeCount }: SidebarItemProps) {
  const Icon = item.icon;
  const content = (
    <>
      <Icon
        weight={isActive ? "fill" : "regular"}
        aria-hidden="true"
        className="size-5.5 shrink-0"
      />
      <span className="sr-only xl:not-sr-only xl:flex-1">{item.label}</span>
      {item.href === null && (
        <span className="sr-only">（{NAV_DISABLED_HINT}）</span>
      )}
      <PendingBadge
        count={badgeCount}
        className="absolute top-1 right-1 xl:static"
      />
    </>
  );

  if (item.href === null) {
    return (
      <span
        aria-disabled="true"
        title={`${item.label}（${NAV_DISABLED_HINT}）`}
        className={cn(ITEM_CLASS, "cursor-not-allowed text-on-chrome/40")}
      >
        {content}
      </span>
    );
  }
  return (
    <Link
      href={item.href}
      aria-current={isActive ? "page" : undefined}
      title={item.label}
      className={cn(
        ITEM_CLASS,
        "pressable focus-ring",
        isActive ? "nav-active font-semibold" : "hover:bg-chrome-fill",
      )}
    >
      {content}
    </Link>
  );
}

/** 桌機側欄（浮動的液態玻璃）：xl 以上顯示完整名稱，lg 收成圖示列，lg 以下改用底部分頁列。 */
export function AppSidebar({ pendingBedCount }: AppSidebarProps) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="主要導覽"
      className="sidebar-chrome sticky top-topbar hidden h-[calc(100dvh-var(--spacing-topbar))] w-rail shrink-0 px-3 py-4 text-on-chrome lg:block xl:w-sidebar"
    >
      <ul className="flex flex-col gap-2">
        {NAV_ITEMS.map((item) => (
          <li key={item.label}>
            <SidebarItem
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
