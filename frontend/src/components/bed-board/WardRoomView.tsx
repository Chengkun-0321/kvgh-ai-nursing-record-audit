import { WardMap } from "@/components/ward-scene/WardMap";
import { useWardSceneMode } from "@/hooks/useWebGLSupport";
import type { WardBedBoard } from "@/lib/api/wards";
import type { BedFilterValue } from "@/lib/verdict";

import { WardBedGrid } from "./WardBedGrid";

type WardRoomViewProps = {
  board: WardBedBoard;
  selectedBedCode?: string;
  activeFilter: BedFilterValue;
  onToggle: (bedCode: string) => void;
  onBackgroundClick: () => void;
};

/** 只有切換到病房才偵測 WebGL；場景不可用時沿用既有 2D 病床格。 */
export function WardRoomView(props: WardRoomViewProps) {
  const { mode, reportSceneError } = useWardSceneMode();
  if (mode === "2d") {
    return (
      <div className="ward-safe">
        <WardBedGrid {...props} />
      </div>
    );
  }
  return (
    <WardMap
      {...props}
      isSceneEnabled={mode === "3d"}
      onSceneError={reportSceneError}
    />
  );
}
