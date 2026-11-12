import type { BedBoardStatus, BedStatus } from "@/lib/api/wards";

/** 病床總覽的篩選值：全部，或指定某個病床狀態。 */
export type BedFilterValue = BedBoardStatus | "ALL";

/** 判斷病床在目前篩選下是否應淡化（保留床位位置，不移除）。 */
export function isBedDimmed(bed: BedStatus, filter: BedFilterValue): boolean {
  return filter !== "ALL" && bed.status !== filter;
}
