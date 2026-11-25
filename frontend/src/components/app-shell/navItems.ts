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
  /** 從病患頁點過去時，是否把目前病人帶到目標頁（網址參數 `patient`） */
  carriesPatient?: boolean;
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
    carriesPatient: true,
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

const PATIENT_PATH = /^\/patients\/([^/]+)/;

/**
 * 導覽項目的實際連結。在病患頁（`/patients/<patientKey>`）點「原始資料」時帶上同一位病人，
 * 不必回到原始資料頁再選一次；其他頁面照原本的連結。
 */
export function navItemHref(
  item: NavItemConfig,
  pathname: string,
): string | null {
  if (item.href === null || !item.carriesPatient) {
    return item.href;
  }
  const encodedKey = PATIENT_PATH.exec(pathname)?.[1];
  if (!encodedKey) {
    return item.href;
  }
  const params = new URLSearchParams({
    patient: decodeURIComponent(encodedKey),
  });
  return `${item.href}?${params.toString()}`;
}

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
