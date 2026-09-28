import type { ReactNode } from "react";

type SettingsLayoutProps = {
  children: ReactNode;
};

// 設定類頁面共用的靜態底色：讓玻璃面板有柔和層次可透
export default function SettingsLayout({ children }: SettingsLayoutProps) {
  return (
    <>
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 page-backdrop"
      />
      <div className="relative mx-auto max-w-7xl px-4 pt-4 pb-8 lg:pt-0 lg:pr-4 lg:pl-0">
        {children}
      </div>
    </>
  );
}
