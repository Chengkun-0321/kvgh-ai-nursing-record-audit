import {
  ArrowsOutSimpleIcon,
  MinusIcon,
  PlusIcon,
} from "@/components/ui/icons";
import type { WardViewId } from "@/lib/wardKit";
import {
  getZoomAvailability,
  MAP_LIMITS,
  type ScaleRange,
} from "@/lib/wardMap";

import { ViewToggle } from "./ViewToggle";

type MapControlsProps = {
  scale: number;
  scaleRange: ScaleRange;
  viewId: WardViewId;
  onViewChange: (viewId: WardViewId) => void;
  onZoom: (factor: number) => void;
  onReset: () => void;
};

/** 固定於畫布外的縮放與視角控制，鍵盤與觸控皆可操作。 */
export function MapControls({
  scale,
  scaleRange,
  viewId,
  onViewChange,
  onZoom,
  onReset,
}: MapControlsProps) {
  const { canZoomIn, canZoomOut } = getZoomAvailability(scale, scaleRange);

  return (
    <div
      data-keep-detail
      className="map-controls glass pointer-events-auto absolute z-20 flex items-center rounded-2xl p-1 shadow-float"
      role="group"
      aria-label="病房地圖控制"
    >
      <button
        type="button"
        aria-label="縮小病房"
        disabled={!canZoomOut}
        onClick={() => onZoom(1 / MAP_LIMITS.zoomStep)}
        className="map-control-button"
      >
        <MinusIcon aria-hidden="true" className="size-5" />
      </button>
      <output
        className="min-w-12 text-center text-footnote tabular-nums"
        aria-label="縮放倍率"
      >
        {Math.round(scale * 100)}%
      </output>
      <button
        type="button"
        aria-label="放大病房"
        disabled={!canZoomIn}
        onClick={() => onZoom(MAP_LIMITS.zoomStep)}
        className="map-control-button"
      >
        <PlusIcon aria-hidden="true" className="size-5" />
      </button>
      <span className="mx-1 h-5 w-px bg-separator" aria-hidden="true" />
      <button
        type="button"
        aria-label="重設病房視野"
        title="重設視野（0）"
        onClick={onReset}
        className="map-control-button"
      >
        <ArrowsOutSimpleIcon aria-hidden="true" className="size-5" />
      </button>
      <span className="mx-1 h-5 w-px bg-separator" aria-hidden="true" />
      <ViewToggle value={viewId} onChange={onViewChange} />
    </div>
  );
}
