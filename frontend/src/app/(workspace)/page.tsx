import { BedBoard } from "@/components/bed-board/BedBoard";
import { createMockWardBedBoard } from "@/lib/api/mockWardData";
import { getWardBedBoard } from "@/lib/api/wards";
import { DEFAULT_WARD_CODE } from "@/lib/constants";

type HomePageProps = {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
};

/** 開發環境可用 `?beds=N` 產生指定床數的虛構病房，正式環境忽略此參數。 */
async function getDevBedCount(
  searchParams: HomePageProps["searchParams"],
): Promise<number | undefined> {
  if (process.env.NODE_ENV === "production") return undefined;
  const { beds } = await searchParams;
  const count = typeof beds === "string" ? Number(beds) : Number.NaN;
  return Number.isFinite(count) ? count : undefined;
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const board = await getWardBedBoard(DEFAULT_WARD_CODE);
  const bedCount = await getDevBedCount(searchParams);

  return (
    <BedBoard
      board={
        bedCount === undefined ? board : createMockWardBedBoard(board, bedCount)
      }
    />
  );
}
