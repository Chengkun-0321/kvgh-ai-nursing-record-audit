import {
  ArrowsOutSimpleIcon,
  MinusIcon,
  PlusIcon,
} from "@/components/ui/icons";
import { MAP_LIMITS } from "@/lib/wardMap";

type MapControlsProps = {
  scale: number;
  onZoom: (factor: number) => void;
  onReset: () => void;
};

/** 固定於畫布外的縮放控制，鍵盤與觸控皆可操作。 */
export function MapControls({ scale, onZoom, onReset }: MapControlsProps) {
  return (
    <div
      data-keep-detail
      className="map-controls glass-chrome absolute z-20 flex items-center rounded-2xl p-1 shadow-float"
      role="group"
      aria-label="病房地圖控制"
    >
      <button
        type="button"
        aria-label="縮小病房"
        disabled={scale <= MAP_LIMITS.minScale}
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
        disabled={scale >= MAP_LIMITS.maxScale}
        onClick={() => onZoom(MAP_LIMITS.zoomStep)}
        className="map-control-button"
      >
        <PlusIcon aria-hidden="true" className="size-5" />
      </button>
      <span className="mx-1 h-5 w-px bg-on-chrome/20" aria-hidden="true" />
      <button
        type="button"
        aria-label="重設病房視野"
        title="重設視野（0）"
        onClick={onReset}
        className="map-control-button"
      >
        <ArrowsOutSimpleIcon aria-hidden="true" className="size-5" />
      </button>
    </div>
  );
}
