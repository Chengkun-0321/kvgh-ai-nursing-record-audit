"use client";

import { useMemo, useState } from "react";

import type { VerdictFilterValue } from "@/lib/verdict";
import { DEFAULT_WARD_VIEW, WARD_KITS, type WardViewId } from "@/lib/wardKit";
import { createCameraChannel } from "@/lib/wardMap";
import { buildWardLayout } from "@/lib/wardLayout";
import { createWardView, getMapFrame, getMapSize } from "@/lib/wardProjection";
import type { WardBedBoard } from "@/types/ward";

import { BedHotspotLayer } from "./BedHotspotLayer";
import { WardMapViewport } from "./WardMapViewport";
import { WardScene } from "./WardScene";

type WardMapProps = {
  board: WardBedBoard;
  selectedBedCode?: string;
  activeFilter: VerdictFilterValue;
  /** 水合完成且瀏覽器支援 WebGL 時才載入 3D 場景；之前只有可操作的 DOM 病床按鈕。 */
  isSceneEnabled: boolean;
  onToggle: (bedCode: string) => void;
  onBackgroundClick: () => void;
  onSceneError: () => void;
};

/**
 * 病房地圖：版面只依床號清單與視角計算，篩選、選床、縮放都不會重新排床。
 * 視角（正視／斜視）由地圖控制列切換，切換時重設視野。
 */
export function WardMap({
  board,
  selectedBedCode,
  activeFilter,
  isSceneEnabled,
  onToggle,
  onBackgroundClick,
  onSceneError,
}: WardMapProps) {
  const [viewId, setViewId] = useState<WardViewId>(DEFAULT_WARD_VIEW);
  const kit = WARD_KITS[viewId];
  const view = useMemo(() => createWardView(kit), [kit]);
  const layout = useMemo(
    () => buildWardLayout(board.beds, kit),
    [board.beds, kit],
  );
  const frame = useMemo(() => getMapFrame(view, layout.bounds), [view, layout]);
  const mapSize = useMemo(() => getMapSize(frame), [frame]);
  const [channel] = useState(createCameraChannel);
  const scene = isSceneEnabled ? (
    <WardScene
      beds={board.beds}
      layout={layout}
      frame={frame}
      activeFilter={activeFilter}
      channel={channel}
      onError={onSceneError}
    />
  ) : undefined;

  return (
    <>
      <WardMapViewport
        mapSize={mapSize}
        channel={channel}
        scene={scene}
        viewId={viewId}
        onViewChange={setViewId}
        selectedBedCode={selectedBedCode}
        onBackgroundClick={onBackgroundClick}
      >
        <BedHotspotLayer
          beds={board.beds}
          layout={layout}
          frame={frame}
          selectedBedCode={selectedBedCode}
          activeFilter={activeFilter}
          onToggle={onToggle}
        />
      </WardMapViewport>
      {board.beds.length === 0 && (
        <p className="pointer-events-none absolute inset-0 m-auto h-fit w-fit rounded-card bg-surface px-8 py-6 text-headline">
          目前沒有床位資料
        </p>
      )}
    </>
  );
}
