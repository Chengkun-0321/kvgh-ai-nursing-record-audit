import {
  BedIcon,
  ChartBarIcon,
  FileTextIcon,
  GearIcon,
  type Icon,
  ListChecksIcon,
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
  /** 手機底部分頁列最多 5 項；尚未推出且較少在手機上使用的項目只在桌機顯示 */
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
    showInMobileTabBar: false,
  },
  {
    label: "原始資料",
    href: "/raw-data",
    icon: FileTextIcon,
    activePathPrefixes: ["/raw-data"],
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
