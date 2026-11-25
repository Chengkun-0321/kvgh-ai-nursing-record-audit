"use client";

import { CircleNotchIcon, SignOutIcon } from "@/components/ui/icons";
import { useLogout } from "@/hooks/useLogout";
import { cn } from "@/lib/utils";

type LogoutButtonProps = {
  className?: string;
};

/** 登出圖示按鈕（44×44px 觸控區）；登出失敗時把錯誤放進 aria-label 與 title 提示。 */
export function LogoutButton({ className }: LogoutButtonProps) {
  const { isPending, errorMessage, signOut } = useLogout();
  const label = errorMessage ? `登出失敗：${errorMessage}，再試一次` : "登出";

  return (
    <button
      type="button"
      onClick={signOut}
      disabled={isPending}
      aria-label={isPending ? "登出中" : label}
      title={label}
      className={cn(
        "grid size-11 shrink-0 pressable place-items-center rounded-full text-ink-secondary focus-ring hover:bg-fill disabled:cursor-not-allowed disabled:opacity-45",
        errorMessage && "text-danger",
        className,
      )}
    >
      {isPending ? (
        <CircleNotchIcon
          aria-hidden="true"
          className="size-5 motion-safe:animate-spin"
        />
      ) : (
        <SignOutIcon aria-hidden="true" className="size-5" />
      )}
    </button>
  );
}
