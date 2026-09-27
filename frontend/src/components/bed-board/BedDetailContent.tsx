"use client";

import Link from "next/link";
import { useId, useState } from "react";

import { CaretRightIcon, UserIcon } from "@/components/ui/icons";
import {
  type SegmentOption,
  SegmentedControl,
} from "@/components/ui/SegmentedControl";
import { VerdictIcon } from "@/components/VerdictIcon";
import { getBedSpriteSrc } from "@/lib/bedSprites";
import { cn } from "@/lib/utils";
import { getWorstVerdict, VERDICT_LABELS } from "@/lib/verdict";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import type { BedStatus } from "@/types/ward";

import { BedPhoto } from "./BedPhoto";
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
};

/** 病床詳情：狀態、病床圖、病患資料、稽核結果與進入病患頁面；桌機面板與手機 sheet 共用。 */
export function BedDetailContent({
  bed,
  businessDate,
  headingId,
}: BedDetailContentProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("findings");
  const panelId = useId();
  const verdict = getWorstVerdict(bed.findings);
  const style = VERDICT_STYLES[verdict];

  return (
    <div className="flex flex-col gap-5">
      <header className="flex items-center justify-between gap-3">
        <h2 id={headingId} className="text-title tabular-nums">
          {bed.bedCode}
        </h2>
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
      </header>

      <div className="relative aspect-4/3 overflow-hidden rounded-card ward-floor">
        <BedPhoto
          src={getBedSpriteSrc(bed.patient, verdict)}
          sizes="(min-width: 1024px) 300px, 80vw"
          className="absolute top-1/2 left-1/2 w-4/5 -translate-x-1/2 -translate-y-[48%]"
        />
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

      <Link
        href={`/patients/${encodeURIComponent(bed.patient.patientKey)}`}
        className="flex min-h-12 pressable items-center gap-3 rounded-full bg-accent px-5 text-headline text-accent-contrast focus-ring"
      >
        <UserIcon aria-hidden="true" className="size-5" />
        <span className="flex-1">進入病人個人頁面</span>
        <CaretRightIcon aria-hidden="true" className="size-4.5" />
      </Link>
    </div>
  );
}
