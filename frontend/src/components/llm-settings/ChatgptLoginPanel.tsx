"use client";

import { useId, useState } from "react";

import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
} from "@/components/ui/controlStyles";
import {
  ArrowSquareOutIcon,
  CheckCircleIcon,
  CopyIcon,
  SignInIcon,
  SignOutIcon,
  WarningCircleIcon,
} from "@/components/ui/icons";
import type { ChatgptLogin } from "@/hooks/useChatgptLogin";
import { formatTime } from "@/lib/format";

type ChatgptLoginPanelProps = {
  login: ChatgptLogin;
};

function PendingLogin({ login }: ChatgptLoginPanelProps) {
  const { user_code: userCode, verification_url: verificationUrl } =
    login.status;
  const [isCopied, setIsCopied] = useState(false);

  async function copyCode() {
    await navigator.clipboard.writeText(userCode ?? "");
    setIsCopied(true);
  }

  return (
    <>
      <p className="text-body text-ink">
        開啟驗證頁面，登入 ChatGPT 後輸入以下驗證碼：
      </p>
      <p className="font-mono text-title tracking-widest text-ink">
        {userCode}
      </p>
      <div className="flex flex-wrap gap-2">
        <a
          href={verificationUrl ?? undefined}
          target="_blank"
          rel="noopener noreferrer"
          className={BUTTON_PRIMARY}
        >
          <ArrowSquareOutIcon aria-hidden="true" className="size-4.5" />
          開啟驗證頁面
        </a>
        <button type="button" onClick={copyCode} className={BUTTON_SECONDARY}>
          <CopyIcon aria-hidden="true" className="size-4.5" />
          {isCopied ? "已複製" : "複製驗證碼"}
        </button>
        <button
          type="button"
          onClick={login.signOut}
          disabled={login.isBusy}
          className={BUTTON_SECONDARY}
        >
          取消登入
        </button>
      </div>
      <p className="text-footnote text-ink-secondary">
        {login.status.expires_at &&
          `驗證碼於 ${formatTime(login.status.expires_at)} 失效。`}
        完成後此處會自動更新。請勿將驗證碼提供給他人。
      </p>
    </>
  );
}

function SignedInLogin({ login }: ChatgptLoginPanelProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p className="flex items-center gap-1.5 text-body text-ink">
        <CheckCircleIcon
          weight="fill"
          aria-hidden="true"
          className="size-5 shrink-0 text-positive"
        />
        已登入 {login.status.account_email ?? "ChatGPT 帳號"}
      </p>
      <button
        type="button"
        onClick={login.signOut}
        disabled={login.isBusy}
        className={BUTTON_SECONDARY}
      >
        <SignOutIcon aria-hidden="true" className="size-4.5" />
        登出
      </button>
    </div>
  );
}

function SignedOutLogin({ login }: ChatgptLoginPanelProps) {
  return (
    <>
      <p className="text-body text-ink">
        尚未登入。需以 ChatGPT Plus／Pro 帳號登入一次，所有「Codex・ChatGPT
        訂閱」設定共用此登入。
      </p>
      <button
        type="button"
        onClick={login.signIn}
        disabled={login.isBusy}
        className={`${BUTTON_PRIMARY} self-start`}
      >
        <SignInIcon aria-hidden="true" className="size-4.5" />
        {login.isBusy ? "取得驗證碼中…" : "以 ChatGPT 帳號登入"}
      </button>
    </>
  );
}

/** ChatGPT 訂閱登入：以裝置碼在 OpenAI 頁面完成登入，token 由後端保存。 */
export function ChatgptLoginPanel({ login }: ChatgptLoginPanelProps) {
  const { state, error_message: lastLoginError } = login.status;
  const errorMessage = login.errorMessage ?? lastLoginError;
  const headingId = useId();

  return (
    <section
      aria-labelledby={headingId}
      aria-live="polite"
      className="flex flex-col gap-3 rounded-xl bg-fill p-4"
    >
      <h3 id={headingId} className="text-headline">
        ChatGPT 帳號
      </h3>
      {state === "signed_in" && <SignedInLogin login={login} />}
      {state === "pending" && <PendingLogin login={login} />}
      {state === "signed_out" && <SignedOutLogin login={login} />}
      {errorMessage && (
        <p className="flex items-start gap-1.5 text-footnote text-danger">
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0"
          />
          {errorMessage}
        </p>
      )}
    </section>
  );
}
