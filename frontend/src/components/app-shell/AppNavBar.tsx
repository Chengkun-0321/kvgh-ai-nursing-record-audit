import type { ReactNode } from "react";

import { NAV_PAGE_ACTIONS_SLOT_ID } from "@/lib/navSlots";
import type { CurrentUser } from "@/types/user";

import { AppStatusCapsule } from "./AppStatusCapsule";
import { BrandLink } from "./BrandLink";
import { MainNavTabs } from "./MainNavTabs";

type AppNavBarProps = {
  user: CurrentUser;
  /** 接在標誌右側的頁面資訊（例如首頁的病房名、床數、稽核日期） */
  context: ReactNode;
};

/**
 * 桌機頂部導覽：三座浮動玻璃膠囊（左標誌＋頁面資訊、中導覽、右頁面操作＋狀態），導覽置中於視窗。
 * 外層不接收指標事件，膠囊之間仍可拖曳下方的病房；lg 以下改用頂列與底部分頁列。
 */
export function AppNavBar({ user, context }: AppNavBarProps) {
  return (
    <div className="pointer-events-none fixed inset-x-4 top-4 z-30 hidden h-nav grid-cols-[1fr_auto_1fr] items-center gap-3 lg:grid">
      <div className="glass pointer-events-auto relative flex h-nav min-w-0 items-center gap-3 justify-self-start rounded-full pr-2 pl-2 shadow-float xl:pr-5">
        <BrandLink labelClassName="sr-only xl:not-sr-only" />
        {context}
      </div>
      <MainNavTabs />
      {/* 頁面操作插槽（首頁的檢視切換）以 portal 放進來，排在狀態膠囊左側 */}
      <div className="flex min-w-0 items-center gap-3 justify-self-end">
        <div
          id={NAV_PAGE_ACTIONS_SLOT_ID.desktop}
          className="pointer-events-auto empty:hidden"
        />
        <AppStatusCapsule user={user} />
      </div>
    </div>
  );
}
