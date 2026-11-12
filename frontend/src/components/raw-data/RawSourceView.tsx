import Link from "next/link";

import type { RawSource } from "@/lib/api/rawData";
import { formatDate } from "@/lib/format";
import { type RawDataSearch, rawDataHref } from "@/lib/rawDataQuery";
import { cn } from "@/lib/utils";

type RawSourceViewProps = {
  source: RawSource;
  businessDates: readonly string[];
  search: RawDataSearch;
};

/** 院方原文：選擇資料日期，顯示當天病人檔的原始 JSON，供與時間軸核對。 */
export function RawSourceView({
  source,
  businessDates,
  search,
}: RawSourceViewProps) {
  return (
    <section aria-label="院方原文" className="flex flex-col gap-3">
      <nav aria-label="資料日期" className="flex flex-wrap gap-1.5">
        {businessDates.map((date) => {
          const isActive = date === source.business_date;
          return (
            <Link
              key={date}
              href={rawDataHref(search, { sourceDate: date })}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "inline-flex min-h-11 items-center rounded-full px-4 text-body tabular-nums focus-ring",
                isActive
                  ? "bg-accent-tint font-semibold text-accent-strong"
                  : "bg-fill hover:bg-fill-strong",
              )}
            >
              {formatDate(date)}
            </Link>
          );
        })}
      </nav>
      <pre className="max-h-[70dvh] overflow-auto rounded-card bg-surface p-4 text-footnote whitespace-pre-wrap shadow-card">
        {source.content}
      </pre>
    </section>
  );
}
