import type { ReactNode } from "react";

import { SettingsNav } from "@/components/settings/SettingsNav";

type SettingsLayoutProps = {
  children: ReactNode;
};

// 設定類頁面共用外框：桌機左側為設定分頁導覽，手機改為頁首上方的橫向膠囊列
export default function SettingsLayout({ children }: SettingsLayoutProps) {
  return (
    <div className="mx-auto flex max-w-[90rem] flex-col gap-4 px-4 pt-4 pb-8 lg:grid lg:grid-cols-[14rem_minmax(0,1fr)] lg:items-start lg:gap-6">
      <SettingsNav />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
