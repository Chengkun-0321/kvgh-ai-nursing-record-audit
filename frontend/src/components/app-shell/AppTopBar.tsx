import Link from "next/link";

import { BellIcon, PlusIcon, UserCircleIcon } from "@/components/ui/icons";
import { USER_ROLE_LABELS } from "@/lib/user";
import type { CurrentUser } from "@/types/user";

import { CurrentTime } from "./CurrentTime";
import { PendingBadge } from "./PendingBadge";

type AppTopBarProps = {
  user: CurrentUser;
  pendingBedCount: number;
};

/**
 * 頂列：淺色液態玻璃浮在內容上方，底緣以漸層遮罩淡出取代分隔線。
 * 鈴鐺與使用者目前只顯示資訊，不做成按鈕，避免看起來可點卻沒有反應。
 */
export function AppTopBar({ user, pendingBedCount }: AppTopBarProps) {
  return (
    <header className="glass sticky top-0 z-40 flex h-topbar items-center gap-3 mask-b-from-85% px-4 lg:px-7">
      <Link
        href="/"
        className="flex min-h-11 items-center gap-2.5 rounded-xl focus-ring"
      >
        <span className="grid size-9 place-items-center rounded-lg bg-ink text-surface">
          <PlusIcon weight="bold" aria-hidden="true" className="size-5" />
        </span>
        <span className="text-headline">護理稽核系統</span>
      </Link>

      <div className="ml-auto flex items-center gap-3 sm:gap-5">
        <CurrentTime className="hidden text-footnote text-ink-secondary tabular-nums sm:block" />
        <span
          role="img"
          aria-label={`待處理病床 ${pendingBedCount} 床`}
          className="relative grid size-9 place-items-center"
        >
          <BellIcon aria-hidden="true" className="size-5.5" />
          <PendingBadge
            count={pendingBedCount}
            className="absolute -top-0.5 -right-0.5"
          />
        </span>
        <span className="flex items-center gap-2">
          <UserCircleIcon
            weight="fill"
            aria-hidden="true"
            className="size-8 text-ink-secondary"
          />
          <span className="sr-only md:not-sr-only md:text-body">
            {USER_ROLE_LABELS[user.role]} {user.name}
          </span>
        </span>
      </div>
    </header>
  );
}
