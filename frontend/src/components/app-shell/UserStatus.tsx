import { UserCircleIcon } from "@/components/ui/icons";
import { USER_ROLE_LABELS } from "@/lib/user";
import { cn } from "@/lib/utils";
import type { CurrentUser } from "@/types/user";

import { CurrentTime } from "./CurrentTime";

type UserStatusProps = {
  user: CurrentUser;
  /** 桌機頂部導覽空間較窄：時間到 2xl、姓名到 xl 才顯示，避免三座膠囊重疊 */
  isCompact?: boolean;
  className?: string;
};

/**
 * 目前時間與使用者：手機放在頂列右側，桌機放在頂部導覽右側的玻璃膠囊。
 * 使用者目前只顯示資訊，不做成按鈕，避免看起來可點卻沒有反應。
 */
export function UserStatus({
  user,
  isCompact = false,
  className,
}: UserStatusProps) {
  return (
    <div className={cn("flex items-center gap-3 sm:gap-4", className)}>
      <CurrentTime
        className={cn(
          "hidden text-footnote text-ink-secondary tabular-nums",
          isCompact ? "2xl:block" : "sm:block",
        )}
      />
      <span className="flex items-center gap-2">
        <UserCircleIcon
          weight="fill"
          aria-hidden="true"
          className="size-8 text-ink-secondary"
        />
        <span
          className={cn(
            "sr-only",
            isCompact
              ? "xl:not-sr-only xl:text-body xl:whitespace-nowrap"
              : "md:not-sr-only md:text-body",
          )}
        >
          {USER_ROLE_LABELS[user.role]} {user.name}
        </span>
      </span>
    </div>
  );
}
