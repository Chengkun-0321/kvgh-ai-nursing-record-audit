import type { CurrentUser } from "@/types/user";

import { BrandLink } from "./BrandLink";
import { UserStatus } from "./UserStatus";

type AppTopBarProps = {
  user: CurrentUser;
  pendingBedCount: number;
};

/**
 * 手機／平板頂列：淺色液態玻璃浮在內容上方，底緣以漸層遮罩淡出取代分隔線。
 * 桌機（lg 以上）改由頂部導覽（`AppNavBar`）取代。
 */
export function AppTopBar({ user, pendingBedCount }: AppTopBarProps) {
  return (
    <header className="glass sticky top-0 z-40 flex h-topbar items-center gap-3 mask-b-from-85% px-4 lg:hidden">
      <BrandLink />
      <UserStatus
        user={user}
        pendingBedCount={pendingBedCount}
        className="ml-auto"
      />
    </header>
  );
}
