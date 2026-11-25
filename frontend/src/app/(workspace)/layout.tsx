import type { ReactNode } from "react";

import { AppNavBar } from "@/components/app-shell/AppNavBar";
import { AppTopBar } from "@/components/app-shell/AppTopBar";
import { MobileTabBar } from "@/components/app-shell/MobileTabBar";
import { getCurrentUser } from "@/lib/api/users";

type WorkspaceLayoutProps = {
  children: ReactNode;
  /** 平行路由 `@navContext`：放在頂部左側膠囊的頁面資訊（目前只有首頁的病房資訊） */
  navContext: ReactNode;
};

// 登入後的工作區外框；登入頁（`app/login`）在此 route group 之外。未登入時 proxy 已導向登入頁，
// 登入失效（後端 401）時由 `getCurrentUser` 經 API client 導向登入頁
export default async function WorkspaceLayout({
  children,
  navContext,
}: WorkspaceLayoutProps) {
  const user = await getCurrentUser();

  return (
    <div className="min-h-dvh">
      {/* 全站共用的暖亞麻底色：白色卡片與玻璃外框都疊在這一層上 */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 page-backdrop"
      />
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-full focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-contrast"
      >
        跳至主要內容
      </a>
      <AppTopBar user={user} context={navContext} />
      <AppNavBar user={user} context={navContext} />
      <main
        id="main-content"
        className="pb-[calc(3.5rem+env(safe-area-inset-bottom))] lg:pt-toolbar lg:pb-0"
      >
        {children}
      </main>
      <MobileTabBar />
    </div>
  );
}
