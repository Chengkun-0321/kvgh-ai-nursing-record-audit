import {
  BedIcon,
  FileTextIcon,
  GearIcon,
  type Icon,
} from "@/components/ui/icons";

export type NavItemConfig = {
  label: string;
  href: string;
  /** 從病患頁點過去時，是否把目前病人帶到目標頁（網址參數 `patient`） */
  carriesPatient?: boolean;
  icon: Icon;
  /** 屬於此項目的路徑前綴，用於標示目前所在位置 */
  activePathPrefixes: readonly string[];
};

// 導覽名稱直接描述內容；只列已實作的頁面，新功能完成後再加入
export const NAV_ITEMS: readonly NavItemConfig[] = [
  {
    label: "病房總覽",
    href: "/",
    icon: BedIcon,
    activePathPrefixes: ["/patients"],
  },
  {
    label: "原始資料",
    href: "/raw-data",
    carriesPatient: true,
    icon: FileTextIcon,
    activePathPrefixes: ["/raw-data"],
  },
  {
    label: "設定",
    href: "/settings/llm",
    icon: GearIcon,
    activePathPrefixes: ["/settings"],
  },
];

const PATIENT_PATH = /^\/patients\/([^/]+)/;

/**
 * 導覽項目的實際連結。在病患頁（`/patients/<patientKey>`）點「原始資料」時帶上同一位病人，
 * 不必回到原始資料頁再選一次；其他頁面照原本的連結。
 */
export function navItemHref(item: NavItemConfig, pathname: string): string {
  if (!item.carriesPatient) {
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
  return (
    pathname === item.href ||
    item.activePathPrefixes.some((prefix) => pathname.startsWith(prefix))
  );
}
