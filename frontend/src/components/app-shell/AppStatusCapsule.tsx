import type { CurrentUser } from "@/types/user";

import { UserStatus } from "./UserStatus";

type AppStatusCapsuleProps = {
  user: CurrentUser;
  pendingBedCount: number;
};

/** 桌機頂部導覽右側的玻璃膠囊：目前時間、待處理數與使用者。 */
export function AppStatusCapsule({
  user,
  pendingBedCount,
}: AppStatusCapsuleProps) {
  return (
    <header className="glass pointer-events-auto relative flex h-nav items-center justify-self-end rounded-full pr-2 pl-4 shadow-float xl:pl-5">
      <UserStatus user={user} pendingBedCount={pendingBedCount} isCompact />
    </header>
  );
}
