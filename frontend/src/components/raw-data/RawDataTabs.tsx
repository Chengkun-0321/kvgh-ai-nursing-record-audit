import Link from "next/link";

import {
  type RawDataSearch,
  type RawDataView,
  rawDataHref,
} from "@/lib/rawDataQuery";
import { cn } from "@/lib/utils";

const TABS: readonly { view: RawDataView; label: string }[] = [
  { view: "timeline", label: "時間軸" },
  { view: "labs", label: "檢驗總表" },
  { view: "source", label: "院方原文" },
];

/** 檢視切換：以連結切換，網址即狀態。 */
export function RawDataTabs({ search }: { search: RawDataSearch }) {
  return (
    <nav
      aria-label="原始資料檢視"
      className="inline-flex gap-1 self-start rounded-full bg-fill p-1"
    >
      {TABS.map(({ view, label }) => {
        const isActive = search.view === view;
        return (
          <Link
            key={view}
            href={rawDataHref(search, { view })}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "inline-flex min-h-11 items-center rounded-full px-4 text-body font-semibold focus-ring",
              isActive
                ? "bg-surface text-ink shadow-card"
                : "text-ink-secondary hover:text-ink",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
