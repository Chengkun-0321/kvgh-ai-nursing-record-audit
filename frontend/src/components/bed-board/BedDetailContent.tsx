"use client";

import Image from "next/image";
import { type ReactNode, useId, useState } from "react";

import {
  type SegmentOption,
  SegmentedControl,
} from "@/components/ui/SegmentedControl";
import { VerdictIcon } from "@/components/VerdictIcon";
import { getPatientPortraitSrc } from "@/lib/bedSprites";
import { cn } from "@/lib/utils";
import { getWorstVerdict, VERDICT_LABELS } from "@/lib/verdict";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import type { BedStatus } from "@/types/ward";

import { FindingList } from "./FindingList";
import { PatientFacts } from "./PatientFacts";

type DetailTab = "findings" | "records" | "vitals" | "more";

// TODO(待決): 護理紀錄、生命徵象、更多資訊的內容待病患頁面討論後提供，目前停用
const DETAIL_TABS: readonly SegmentOption<DetailTab>[] = [
  { value: "findings", label: "異常摘要" },
  { value: "records", label: "護理紀錄", disabledHint: "即將推出" },
  { value: "vitals", label: "生命徵象", disabledHint: "即將推出" },
  { value: "more", label: "更多資訊", disabledHint: "即將推出" },
];

type BedDetailContentProps = {
  bed: BedStatus;
  businessDate: string;
  headingId: string;
  /** 標頭右側的操作（例如桌機大卡的關閉鈕） */
  headerAction?: ReactNode;
};

/** 病床詳情：狀態、病床圖、病患資料與稽核結果；桌機大卡與手機 sheet 共用（進入病患頁面按鈕由外層放置）。 */
export function BedDetailContent({
  bed,
  businessDate,
  headingId,
  headerAction,
}: BedDetailContentProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("findings");
  const panelId = useId();
  const verdict = getWorstVerdict(bed.findings);
  const style = VERDICT_STYLES[verdict];

  return (
    <div className="flex flex-col gap-5">
      <header className="flex items-center gap-3">
        <h2 id={headingId} className="text-title tabular-nums">
          {bed.bedCode}
        </h2>
        {/* 淡色底疊在液態玻璃上對比不足，先墊一層實色 surface */}
        <span className="rounded-full bg-surface">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full py-1 pr-3 pl-1.5 text-footnote font-semibold",
              style.tint,
              style.text,
            )}
          >
            <VerdictIcon verdict={verdict} />
            {VERDICT_LABELS[verdict]}
          </span>
        </span>
        {headerAction && <div className="ml-auto">{headerAction}</div>}
      </header>

      <div className="relative aspect-4/3 overflow-hidden rounded-2xl bg-scene-wall">
        <Image
          src={getPatientPortraitSrc(bed.patient)}
          alt=""
          fill
          sizes="(min-width: 1024px) 328px, 90vw"
          className="object-cover"
        />
        <span className="absolute right-2 bottom-2 rounded-md bg-surface/90 px-2 py-0.5 text-caption text-ink-secondary">
          示意影像
        </span>
      </div>

      <PatientFacts patient={bed.patient} businessDate={businessDate} />

      <SegmentedControl
        options={DETAIL_TABS}
        value={activeTab}
        onChange={setActiveTab}
        ariaLabel="病床詳情分類"
        panelId={panelId}
      />
      <div id={panelId} role="tabpanel">
        <FindingList findings={bed.findings} />
      </div>
    </div>
  );
}
