import type { AuditFindingSummary, BedStatus, Verdict } from "@/types/ward";

/** 病床總覽的篩選值：全部，或指定某個最嚴重判定。 */
export type VerdictFilterValue = Verdict | "ALL";

/** 由嚴重到輕的判定順序，用於排序、狀態列與摘要文字。 */
export const VERDICTS_BY_SEVERITY: readonly Verdict[] = [
  "ERROR",
  "WARNING",
  "NEEDS_REVIEW",
  "PASS",
];

// 用語描述「紀錄」狀態，避免被誤讀為病患病情或指責護理師
export const VERDICT_LABELS: Record<Verdict, string> = {
  ERROR: "缺漏",
  WARNING: "需確認",
  NEEDS_REVIEW: "無法判定",
  PASS: "紀錄完整",
};

const SEVERITY_RANK: Record<Verdict, number> = {
  PASS: 0,
  NEEDS_REVIEW: 1,
  WARNING: 2,
  ERROR: 3,
};

/** 取得最嚴重的判定；沒有任何稽核結果時視為 `PASS`。 */
export function getWorstVerdict(
  findings: readonly AuditFindingSummary[],
): Verdict {
  return findings.reduce<Verdict>(
    (worst, finding) =>
      SEVERITY_RANK[finding.verdict] > SEVERITY_RANK[worst]
        ? finding.verdict
        : worst,
    "PASS",
  );
}

/** 取出非 `PASS` 的稽核結果，並依嚴重度由高到低排序。 */
export function getPendingFindings(
  findings: readonly AuditFindingSummary[],
): AuditFindingSummary[] {
  return findings
    .filter((finding) => finding.verdict !== "PASS")
    .sort((a, b) => SEVERITY_RANK[b.verdict] - SEVERITY_RANK[a.verdict]);
}

function createEmptyVerdictCounts(): Record<Verdict, number> {
  return { ERROR: 0, WARNING: 0, NEEDS_REVIEW: 0, PASS: 0 };
}

/** 依各床最嚴重判定統計床數，供狀態列顯示。 */
export function countBedsByWorstVerdict(
  beds: readonly BedStatus[],
): Record<Verdict, number> {
  const counts = createEmptyVerdictCounts();
  for (const bed of beds) {
    counts[getWorstVerdict(bed.findings)] += 1;
  }
  return counts;
}

/** 產生病床下方的摘要文字，例如「缺漏 1 項・需確認 2 項」。 */
export function describeFindingCounts(
  findings: readonly AuditFindingSummary[],
): string {
  const counts = createEmptyVerdictCounts();
  for (const finding of findings) {
    counts[finding.verdict] += 1;
  }
  const parts = VERDICTS_BY_SEVERITY.filter(
    (verdict) => verdict !== "PASS" && counts[verdict] > 0,
  ).map((verdict) => `${VERDICT_LABELS[verdict]} ${counts[verdict]} 項`);
  return parts.length > 0 ? parts.join("・") : VERDICT_LABELS.PASS;
}

/** 統計最嚴重判定不是 `PASS` 的床數（待處理病床）。 */
export function countPendingBeds(beds: readonly BedStatus[]): number {
  return beds.filter((bed) => getWorstVerdict(bed.findings) !== "PASS").length;
}

/** 判斷病床在目前篩選下是否應淡化（保留床位位置，不移除）。 */
export function isBedDimmed(
  bed: BedStatus,
  filter: VerdictFilterValue,
): boolean {
  return filter !== "ALL" && getWorstVerdict(bed.findings) !== filter;
}
