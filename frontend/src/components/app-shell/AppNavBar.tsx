import type { CurrentUser } from "@/types/user";

import { AppStatusCapsule } from "./AppStatusCapsule";
import { BrandLink } from "./BrandLink";
import { MainNavTabs } from "./MainNavTabs";

type AppNavBarProps = {
  user: CurrentUser;
  pendingBedCount: number;
};

/**
 * 桌機頂部導覽：三座浮動玻璃膠囊（左標誌、中導覽、右狀態），導覽置中於視窗。
 * 外層不接收指標事件，膠囊之間仍可拖曳下方的病房；lg 以下改用頂列與底部分頁列。
 */
export function AppNavBar({ user, pendingBedCount }: AppNavBarProps) {
  return (
    <div className="pointer-events-none fixed inset-x-4 top-4 z-30 hidden h-nav grid-cols-[1fr_auto_1fr] items-center gap-3 lg:grid">
      <BrandLink
        className="glass pointer-events-auto relative h-nav justify-self-start rounded-full pr-2 pl-2 shadow-float xl:pr-5"
        labelClassName="sr-only xl:not-sr-only"
      />
      <MainNavTabs pendingBedCount={pendingBedCount} />
      <AppStatusCapsule user={user} pendingBedCount={pendingBedCount} />
    </div>
  );
}
