import type { CurrentUser } from "@/types/user";

import { UserStatus } from "./UserStatus";

type AppStatusCapsuleProps = {
  user: CurrentUser;
};

/** 桌機頂部導覽右側的玻璃膠囊：目前時間與使用者。 */
export function AppStatusCapsule({ user }: AppStatusCapsuleProps) {
  return (
    <header className="glass pointer-events-auto relative flex h-nav items-center justify-self-end rounded-full pr-2 pl-4 shadow-float xl:pl-5">
      <UserStatus user={user} isCompact />
    </header>
  );
}
