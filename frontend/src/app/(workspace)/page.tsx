import { BedBoard } from "@/components/bed-board/BedBoard";
import { getWardBedBoard } from "@/lib/api/wards";
import { DEFAULT_WARD_CODE } from "@/lib/constants";

export default async function HomePage() {
  const board = await getWardBedBoard(DEFAULT_WARD_CODE);

  return <BedBoard board={board} />;
}
