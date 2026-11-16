import Image from "next/image";
import type { ReactNode } from "react";

import type { AuditRuleView } from "@/hooks/useAuditRuns";
import { useMediaQuery } from "@/hooks/useMediaQuery";

import { AuditRuleCard } from "./AuditRuleCard";

// 環狀在 1400px 以上才能放下 12 項（卡片不重疊的條件見 patient-audit.css）；項目較少時於桌機一律環狀
const WIDE_QUERY = "(min-width: 87.5rem)";
const RING_MAX_COMPACT_COUNT = 8;

type AuditRuleListProps = {
  /** 區塊左上角的內容（病患識別）。 */
  title: ReactNode;
  rules: AuditRuleView[];
  pageDate: string;
  onOpen: (ruleCode: string) => void;
  onRun: (ruleCode: string) => void;
};

/**
 * 稽核項目清單。lg 以上為環狀：中央示意圖，項目沿橢圓軌道均勻排列（定位在 patient-audit.css）；
 * 病患識別在環狀時疊在左上角的空白處，卡片格時排在清單上方。
 * 項目多且桌機寬度不足時改為均勻的卡片格；手機與平板為卡片格。數量與順序完全來自後端 rules。
 */
export function AuditRuleList({
  title,
  rules,
  pageDate,
  onOpen,
  onRun,
}: AuditRuleListProps) {
  // 環狀的定位只在 lg 以上生效（CSS），因此手機上的 data-layout 不影響版面；
  // 不以 matchMedia 決定 data-layout，避免伺服器端輸出與首屏不符。
  const isWide = useMediaQuery(WIDE_QUERY);
  const layout =
    rules.length <= RING_MAX_COMPACT_COUNT || isWide ? "ring" : "grid";
  return (
    <div className="audit-stage" data-layout={layout}>
      {title}
      <figure className="audit-hub">
        <Image
          src="/images/patients/patient-neutral.jpg"
          alt="病患示意影像（非真實病患）"
          width={1448}
          height={1086}
          sizes="26rem"
          className="h-auto w-full rounded-card"
        />
        <figcaption className="mt-2 text-center text-caption text-ink-secondary">
          示意影像
        </figcaption>
      </figure>
      <ol className="audit-ring" data-count={rules.length}>
        {rules.map((rule) => (
          <AuditRuleCard
            key={rule.rule_code}
            rule={rule}
            pageDate={pageDate}
            onOpen={onOpen}
            onRun={onRun}
          />
        ))}
      </ol>
    </div>
  );
}
