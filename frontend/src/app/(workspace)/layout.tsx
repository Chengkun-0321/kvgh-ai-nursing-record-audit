import type { ReactNode } from "react";

import { AppNavBar } from "@/components/app-shell/AppNavBar";
import { AppTopBar } from "@/components/app-shell/AppTopBar";
import { MobileTabBar } from "@/components/app-shell/MobileTabBar";
import { getCurrentUser } from "@/lib/api/users";
import { getWardBedBoard } from "@/lib/api/wards";
import { DEFAULT_WARD_CODE } from "@/lib/constants";
import { countPendingBeds } from "@/lib/verdict";

type WorkspaceLayoutProps = {
  children: ReactNode;
};

// 登入後的工作區外框；登入頁（待決）之後放在此 route group 之外
export default async function WorkspaceLayout({
  children,
}: WorkspaceLayoutProps) {
  const [user, board] = await Promise.all([
    getCurrentUser(),
    getWardBedBoard(DEFAULT_WARD_CODE),
  ]);
  const pendingBedCount = countPendingBeds(board.beds);

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
      <AppTopBar user={user} pendingBedCount={pendingBedCount} />
      <AppNavBar user={user} pendingBedCount={pendingBedCount} />
      <main
        id="main-content"
        className="pb-[calc(3.5rem+env(safe-area-inset-bottom))] lg:pt-toolbar lg:pb-0"
      >
        {children}
      </main>
      <MobileTabBar pendingBedCount={pendingBedCount} />
    </div>
  );
}
