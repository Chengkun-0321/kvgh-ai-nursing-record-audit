import type { ReactNode } from "react";

import { NAV_PAGE_ACTIONS_SLOT_ID } from "@/lib/navSlots";
import type { CurrentUser } from "@/types/user";

import { BrandLink } from "./BrandLink";
import { UserStatus } from "./UserStatus";

type AppTopBarProps = {
  user: CurrentUser;
  /** 接在標誌右側的頁面資訊（例如首頁的病房名、床數、稽核日期） */
  context: ReactNode;
};

/**
 * 手機／平板頂列：淺色液態玻璃浮在內容上方，底緣以漸層遮罩淡出取代分隔線。
 * 桌機（lg 以上）改由頂部導覽（`AppNavBar`）取代。
 */
export function AppTopBar({ user, context }: AppTopBarProps) {
  return (
    <header className="group/topbar glass sticky top-0 z-40 flex h-topbar items-center gap-3 mask-b-from-85% px-4 lg:hidden">
      {/* 手機上有頁面資訊時，系統名稱只留給螢幕閱讀器，讓病房資訊完整顯示 */}
      <BrandLink labelClassName="max-sm:group-has-[[data-nav-context]]/topbar:sr-only" />
      {context}
      <div className="ml-auto flex items-center gap-2">
        <div id={NAV_PAGE_ACTIONS_SLOT_ID.mobile} className="empty:hidden" />
        <UserStatus user={user} />
      </div>
    </header>
  );
}
