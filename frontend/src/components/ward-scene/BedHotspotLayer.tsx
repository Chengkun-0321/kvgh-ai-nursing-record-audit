"use client";

import { useRef } from "react";

import { WARD_TITLE_ID } from "@/components/bed-board/WardTitle";
import { useMapKeyframe } from "@/hooks/useMapKeyframe";
import { isBedDimmed, type VerdictFilterValue } from "@/lib/verdict";
import type { WardLayout } from "@/lib/wardLayout";
import {
  getBedHotspot,
  getBedLabelPoint,
  type MapFrame,
} from "@/lib/wardProjection";
import type { BedStatus } from "@/types/ward";

import { BedHotspot } from "./BedHotspot";

type BedHotspotLayerProps = {
  beds: readonly BedStatus[];
  layout: WardLayout;
  frame: MapFrame;
  selectedBedCode?: string;
  activeFilter: VerdictFilterValue;
  onToggle: (bedCode: string) => void;
};

/** 每張床的可點範圍與標籤相對位置都相同，只算一次並寫成 CSS 變數。 */
function getHotspotVars(frame: MapFrame) {
  const origin = { x: 0, z: 0 };
  const rect = getBedHotspot(origin, frame);
  const label = getBedLabelPoint(origin, frame);
  return {
    "--bed-hit-w": `${rect.width}px`,
    "--bed-hit-h": `${rect.height}px`,
    "--bed-label-x": `${label.x - rect.x}px`,
    "--bed-label-y": `${label.y - rect.y}px`,
  };
}

/** DOM 病床按鈕層：與 3D 場景同一地圖座標，鍵盤、螢幕報讀與點選都在這一層。 */
export function BedHotspotLayer({
  beds,
  layout,
  frame,
  selectedBedCode,
  activeFilter,
  onToggle,
}: BedHotspotLayerProps) {
  const listRef = useRef<HTMLUListElement>(null);
  const positions = layout.beds.map((slot) =>
    getBedHotspot(slot.anchor, frame),
  );
  useMapKeyframe(listRef, getHotspotVars(frame));

  return (
    <ul
      ref={listRef}
      className="bed-hotspots absolute inset-0"
      aria-labelledby={WARD_TITLE_ID}
    >
      {beds.map((bed, index) => {
        const position = positions[index];
        if (!position) return null;
        return (
          <BedHotspot
            key={bed.bedCode}
            bed={bed}
            position={position}
            isSelected={bed.bedCode === selectedBedCode}
            isDimmed={isBedDimmed(bed, activeFilter)}
            onToggle={onToggle}
          />
        );
      })}
    </ul>
  );
}
