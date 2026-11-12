import { BedBoard } from "@/components/bed-board/BedBoard";
import { getDefaultWardCode, getWardBedBoard } from "@/lib/api/wards";

export default async function HomePage() {
  const board = await getWardBedBoard(await getDefaultWardCode());
  return <BedBoard board={board} />;
}
