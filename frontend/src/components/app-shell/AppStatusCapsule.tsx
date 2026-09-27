import type { CurrentUser } from "@/types/user";

import { UserStatus } from "./UserStatus";

type AppStatusCapsuleProps = {
  user: CurrentUser;
  pendingBedCount: number;
};

/**
 * 桌機右上角的玻璃膠囊：取代滿寬頂列，讓場景直達視窗上緣；
 * 與側欄、病房標題對齊同一條上緣（top-4），詳情卡由 `--spacing-toolbar` 以下開始。
 */
export function AppStatusCapsule({
  user,
  pendingBedCount,
}: AppStatusCapsuleProps) {
  return (
    <header className="glass fixed top-4 right-4 z-30 hidden h-13 items-center rounded-full pr-2 pl-5 shadow-float lg:flex">
      <UserStatus user={user} pendingBedCount={pendingBedCount} />
    </header>
  );
}
