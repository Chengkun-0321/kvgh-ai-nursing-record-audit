"use client";

import { BUTTON_PRIMARY } from "@/components/ui/controlStyles";
import {
  CircleNotchIcon,
  SignInIcon,
  WarningCircleIcon,
} from "@/components/ui/icons";
import { TextField } from "@/components/ui/TextField";
import { useLoginForm } from "@/hooks/useLoginForm";
import { cn } from "@/lib/utils";

type LoginFormProps = {
  /** 登入後要回到的站內路徑（已在伺服器端過濾外站網址） */
  nextPath: string;
};

/** 帳密登入表單：按鈕或 Enter 送出；帳密任一為空或送出中時停用登入按鈕。 */
export function LoginForm({ nextPath }: LoginFormProps) {
  const form = useLoginForm(nextPath);

  return (
    <form
      onSubmit={form.submit}
      className="mt-6 flex flex-col gap-4"
      noValidate
    >
      <TextField
        id="login-username"
        label="帳號："
        value={form.username}
        onChange={form.setUsername}
        autoComplete="username"
        spellCheck={false}
      />
      <TextField
        id="login-password"
        label="密碼："
        type="password"
        value={form.password}
        onChange={form.setPassword}
        autoComplete="current-password"
      />
      <button
        type="submit"
        disabled={!form.canSubmit}
        aria-busy={form.isPending || undefined}
        className={cn(BUTTON_PRIMARY, "mt-2 w-full")}
      >
        {form.isPending ? (
          <CircleNotchIcon
            aria-hidden="true"
            className="size-4.5 motion-safe:animate-spin"
          />
        ) : (
          <SignInIcon aria-hidden="true" className="size-4.5" />
        )}
        {form.isPending ? "登入中…" : "登入"}
      </button>
      {/* 固定保留 alert 區域，錯誤出現時螢幕閱讀器會立即讀出 */}
      <div role="alert" className="min-h-5">
        {form.errorMessage && (
          <p className="flex items-start gap-1 text-footnote text-danger">
            <WarningCircleIcon
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            {form.errorMessage}
          </p>
        )}
      </div>
    </form>
  );
}
