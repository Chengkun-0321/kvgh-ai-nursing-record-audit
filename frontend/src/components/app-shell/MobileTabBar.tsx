"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import {
  isNavItemActive,
  NAV_ITEMS,
  type NavItemConfig,
  navItemHref,
} from "./navItems";

type TabItemProps = {
  item: NavItemConfig;
  /** 依目前頁面算出的連結 */
  href: string;
  isActive: boolean;
};

function TabItem({ item, href, isActive }: TabItemProps) {
  const Icon = item.icon;
  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "relative flex min-h-12 pressable flex-col items-center justify-center gap-0.5 rounded-xl text-tab whitespace-nowrap focus-ring",
        isActive ? "font-semibold text-ink" : "text-ink-secondary",
      )}
    >
      <Icon
        weight={isActive ? "fill" : "regular"}
        aria-hidden="true"
        className="size-6"
      />
      {item.label}
    </Link>
  );
}

/** 手機／平板的底部分頁列，避開 iOS 底部安全區域。 */
export function MobileTabBar() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="主要導覽"
      className="glass fixed inset-x-0 bottom-0 z-30 pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <ul className="grid grid-cols-3 px-2 pt-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.label}>
            <TabItem
              item={item}
              href={navItemHref(item, pathname)}
              isActive={isNavItemActive(item, pathname)}
            />
          </li>
        ))}
      </ul>
    </nav>
  );
}
