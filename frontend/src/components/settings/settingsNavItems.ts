import {
  ClockCountdownIcon,
  CpuIcon,
  type Icon,
  ShieldCheckIcon,
  UsersThreeIcon,
} from "@/components/ui/icons";

export type SettingsNavItemConfig = {
  label: string;
  /** 尚未實作的設定頁為 `null`，以停用狀態顯示 */
  href: string | null;
  icon: Icon;
};

// 新增設定頁時在此加一項；未實作的項目先停用，保留位置讓使用者預期之後的功能
export const SETTINGS_NAV_ITEMS: readonly SettingsNavItemConfig[] = [
  { label: "LLM 模型", href: "/settings/llm", icon: CpuIcon },
  { label: "稽核規則", href: null, icon: ShieldCheckIcon },
  { label: "使用者與權限", href: null, icon: UsersThreeIcon },
  { label: "批次排程", href: null, icon: ClockCountdownIcon },
];

/** 判斷設定分頁是否為目前所在頁面（含其子路徑）。 */
export function isSettingsNavItemActive(
  item: SettingsNavItemConfig,
  pathname: string,
): boolean {
  return item.href !== null && pathname.startsWith(item.href);
}
