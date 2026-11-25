import { connection } from "next/server";

import { BedBoard } from "@/components/bed-board/BedBoard";
import { BoardRefresher } from "@/components/bed-board/BoardRefresher";
import { getDefaultWardCode, getWardBedBoard } from "@/lib/api/wards";

// 每次開啟都向後端讀取病房資料；不加的話 next build 會在建置時預先渲染（需連後端，且會凍結成快照）
export default async function HomePage() {
  await connection();
  const board = await getWardBedBoard(await getDefaultWardCode());
  return (
    <>
      <BoardRefresher />
      <BedBoard board={board} />
    </>
  );
}
