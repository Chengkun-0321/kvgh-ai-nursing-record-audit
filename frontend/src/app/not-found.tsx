import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm rounded-panel bg-surface p-8 text-center shadow-float">
        <h1 className="text-title">找不到此頁面</h1>
        <p className="mt-2 text-body text-ink-secondary">
          網址可能有誤，或該病患已不在目前病房。
        </p>
        <Link
          href="/"
          className="mt-6 flex h-11 pressable items-center justify-center rounded-full bg-accent text-headline text-accent-contrast focus-ring"
        >
          返回病房總覽
        </Link>
      </div>
    </main>
  );
}
