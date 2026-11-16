import { BedBoard } from "@/components/bed-board/BedBoard";
import { BoardRefresher } from "@/components/bed-board/BoardRefresher";
import { getDefaultWardCode, getWardBedBoard } from "@/lib/api/wards";

export default async function HomePage() {
  const board = await getWardBedBoard(await getDefaultWardCode());
  return (
    <>
      <BoardRefresher />
      <BedBoard board={board} />
    </>
  );
}
