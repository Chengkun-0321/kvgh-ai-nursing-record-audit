"use client";

import { WarningCircleIcon } from "@/components/ui/icons";

type ErrorPageProps = {
  error: Error & { digest?: string };
  retry: () => void;
};

export default function ErrorPage({ retry }: ErrorPageProps) {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm rounded-panel bg-surface p-8 text-center shadow-float">
        <WarningCircleIcon
          weight="fill"
          aria-hidden="true"
          className="mx-auto size-10 text-verdict-error"
        />
        <h1 className="mt-4 text-title">資料載入失敗</h1>
        <p className="mt-2 text-body text-ink-secondary">
          暫時無法取得病房資料，請稍後再試。
        </p>
        <button
          type="button"
          onClick={retry}
          className="mt-6 h-11 w-full pressable rounded-full bg-accent text-headline text-accent-contrast focus-ring"
        >
          重新載入
        </button>
      </div>
    </main>
  );
}
