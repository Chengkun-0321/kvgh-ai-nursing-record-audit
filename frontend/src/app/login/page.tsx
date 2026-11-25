import type { Metadata } from "next";

import { LoginForm } from "@/components/auth/LoginForm";
import { NEXT_PARAM, sanitizeNextPath } from "@/lib/auth";

export const metadata: Metadata = {
  title: "登入｜護理稽核系統",
};

type LoginPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

/** demo 登入頁：不在工作區外框內；登入後回到 `?next=` 指定的站內路徑。 */
export default async function LoginPage({ searchParams }: LoginPageProps) {
  const rawNext = (await searchParams)[NEXT_PARAM];
  const nextPath = sanitizeNextPath(
    typeof rawNext === "string" ? rawNext : null,
  );

  return (
    <div className="flex min-h-dvh items-center justify-center px-4 py-10">
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 page-backdrop"
      />
      <main className="w-full max-w-sm rounded-panel bg-surface p-8 shadow-float">
        <h1 className="text-title">AI 護理稽核系統 demo</h1>
        <LoginForm nextPath={nextPath} />
      </main>
    </div>
  );
}
