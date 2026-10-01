import {
  BedIcon,
  ChartBarIcon,
  GearIcon,
  type Icon,
  ListChecksIcon,
  NotebookIcon,
  WarningCircleIcon,
} from "@/components/ui/icons";

export type NavItemConfig = {
  label: string;
  /** 尚未實作的頁面為 `null`，以停用狀態顯示 */
  href: string | null;
  icon: Icon;
  /** 屬於此項目的路徑前綴，用於標示目前所在位置 */
  activePathPrefixes: readonly string[];
  hasPendingBadge: boolean;
  /** 手機底部分頁列最多 5 項；`false` 的項目只出現在桌機頂部導覽 */
  showInMobileTabBar: boolean;
};

// 導覽名稱直接描述內容；未實作的頁面先停用，保留位置讓使用者預期之後的功能
export const NAV_ITEMS: readonly NavItemConfig[] = [
  {
    label: "病房總覽",
    href: "/",
    icon: BedIcon,
    activePathPrefixes: ["/patients"],
    hasPendingBadge: false,
    showInMobileTabBar: true,
  },
  {
    // 瀏覽 mock_data 的虛構紀錄（見 ADR 0010），屬開發驗證用途，手機分頁列不放
    label: "護理紀錄",
    href: "/nursing-records",
    icon: NotebookIcon,
    activePathPrefixes: ["/nursing-records"],
    hasPendingBadge: false,
    showInMobileTabBar: false,
  },
  {
    label: "待處理項目",
    href: null,
    icon: ListChecksIcon,
    activePathPrefixes: [],
    hasPendingBadge: true,
    showInMobileTabBar: true,
  },
  {
    label: "異常紀錄",
    href: null,
    icon: WarningCircleIcon,
    activePathPrefixes: [],
    hasPendingBadge: false,
    showInMobileTabBar: true,
  },
  {
    label: "統計報表",
    href: null,
    icon: ChartBarIcon,
    activePathPrefixes: [],
    hasPendingBadge: false,
    showInMobileTabBar: true,
  },
  {
    label: "設定",
    href: "/settings/llm",
    icon: GearIcon,
    activePathPrefixes: ["/settings"],
    hasPendingBadge: false,
    showInMobileTabBar: true,
  },
];

export const MOBILE_TAB_ITEMS: readonly NavItemConfig[] = NAV_ITEMS.filter(
  (item) => item.showInMobileTabBar,
);

export const NAV_DISABLED_HINT = "即將推出";

/** 判斷導覽項目是否為目前所在頁面。 */
export function isNavItemActive(
  item: NavItemConfig,
  pathname: string,
): boolean {
  if (item.href === null) {
    return false;
  }
  return (
    pathname === item.href ||
    item.activePathPrefixes.some((prefix) => pathname.startsWith(prefix))
  );
}
