import { UserCircleIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";
import type { CurrentUser } from "@/types/user";

import { CurrentTime } from "./CurrentTime";
import { LogoutButton } from "./LogoutButton";

type UserStatusProps = {
  user: CurrentUser;
  /** 桌機頂部導覽空間較窄：時間到 2xl、帳號到 xl 才顯示，避免三座膠囊重疊 */
  isCompact?: boolean;
  className?: string;
};

/**
 * 目前時間、登入帳號與登出按鈕：手機放在頂列右側，桌機放在頂部導覽右側的玻璃膠囊。
 * 帳號只顯示資訊（demo 登入沒有角色資料）；登出是旁邊獨立的圖示按鈕。
 */
export function UserStatus({
  user,
  isCompact = false,
  className,
}: UserStatusProps) {
  return (
    <div className={cn("flex items-center gap-2 sm:gap-3", className)}>
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
          <span className="sr-only">登入帳號：</span>
          {user.username}
        </span>
      </span>
      <LogoutButton />
    </div>
  );
}
