"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { cn } from "@/lib/utils";

import {
  isNavItemActive,
  NAV_ITEMS,
  type NavItemConfig,
  navItemHref,
} from "./navItems";

type NavTabProps = {
  item: NavItemConfig;
  /** 依目前頁面算出的連結 */
  href: string;
  isActive: boolean;
};

// 導覽列不隨換頁重新掛載，選取底色因此能以 spring 從上一頁滑到下一頁
const INDICATOR_LAYOUT_ID = "main-nav-indicator";

function NavTab({ item, href, isActive }: NavTabProps) {
  const Icon = item.icon;
  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "relative flex min-h-11 pressable items-center gap-2 rounded-full px-4 text-body whitespace-nowrap focus-ring",
        isActive ? "font-semibold text-ink" : "hover:bg-fill",
      )}
    >
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
    </Link>
  );
}

/** 桌機頂部導覽中央的玻璃膠囊：目前頁以白色實色膠囊標示，換頁時以 spring 滑動。 */
export function MainNavTabs() {
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
              href={navItemHref(item, pathname)}
              isActive={isNavItemActive(item, pathname)}
            />
          </li>
        ))}
      </ul>
    </nav>
  );
}
