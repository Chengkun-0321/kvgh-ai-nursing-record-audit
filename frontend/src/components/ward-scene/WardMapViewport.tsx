"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

import type { WardViewId } from "@/lib/wardKit";
import {
  type CameraChannel,
  getBedButtonId,
  MAP_LIMITS,
  type MapSize,
  type ScaleRange,
} from "@/lib/wardMap";
import { WardMapController } from "@/lib/wardMapController";

import { MapControls } from "./MapControls";

type WardMapViewportProps = {
  /** 可點的 DOM 疊層（隨地圖平移縮放）。 */
  children: ReactNode;
  /** 3D 場景（固定鋪滿視窗，由 channel 同步相機）。 */
  scene?: ReactNode;
  mapSize: MapSize;
  channel: CameraChannel;
  viewId: WardViewId;
  onViewChange: (viewId: WardViewId) => void;
  selectedBedCode?: string;
  onBackgroundClick: () => void;
};

/**
 * 世界座標與介面分離：縮放只改變場景，面板、標題與控制列不縮放。
 * 地圖視窗鋪滿整個畫面（外框疊在場景上），病房的縮放與夾限以 `.ward-safe` 安全區為準。
 */
export function WardMapViewport({
  children,
  scene,
  mapSize,
  channel,
  viewId,
  onViewChange,
  selectedBedCode,
  onBackgroundClick,
}: WardMapViewportProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const worldRef = useRef<HTMLDivElement>(null);
  const controller = useRef<WardMapController | null>(null);
  const lastViewId = useRef(viewId);
  const backgroundClickRef = useRef(onBackgroundClick);
  const [scale, setScale] = useState(1);
  const [scaleRange, setScaleRange] = useState<ScaleRange>({
    min: 1,
    max: MAP_LIMITS.maxScale,
  });

  useEffect(() => {
    backgroundClickRef.current = onBackgroundClick;
  }, [onBackgroundClick]);

  useEffect(() => {
    const viewport = viewportRef.current;
    const world = worldRef.current;
    if (!viewport || !world) return;
    const map = new WardMapController({
      viewport,
      world,
      onScale: setScale,
      onScaleRange: setScaleRange,
      onBackgroundClick: () => backgroundClickRef.current(),
      onPaint: (camera) => {
        world.dataset.ready = "true";
        channel.publish(camera);
      },
    });
    controller.current = map;
    return () => {
      map.destroy();
      controller.current = null;
    };
  }, [channel]);

  useEffect(() => {
    controller.current?.setWorldSize(mapSize);
  }, [mapSize]);

  // 切換視角後病房尺寸不同，回到完整顯示的初始視野（排在 setWorldSize 之後執行）
  useEffect(() => {
    if (lastViewId.current === viewId) return;
    lastViewId.current = viewId;
    controller.current?.reset();
  }, [viewId]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const bed = selectedBedCode
        ? document.getElementById(getBedButtonId(selectedBedCode))
        : null;
      if (bed) controller.current?.reveal(bed);
      else controller.current?.refresh();
    });
    return () => cancelAnimationFrame(frame);
  }, [selectedBedCode]);

  return (
    <>
      <div
        ref={viewportRef}
        data-keep-detail
        tabIndex={0}
        role="region"
        aria-label="可縮放拖曳的病房地圖"
        aria-describedby="map-instructions"
        className="ward-map absolute inset-0 overflow-clip focus-ring"
      >
        {scene}
        <div
          ref={worldRef}
          className="ward-world absolute top-0 left-0 origin-top-left"
        >
          {children}
        </div>
      </div>
      <p id="map-instructions" className="sr-only">
        滾輪縮放，按住拖曳移動；觸控可雙指縮放。方向鍵移動，加減鍵縮放，0 或
        Home 重設。Tab 選取病床，Enter 開啟詳情，Esc 關閉。
      </p>
      <div className="ward-safe">
        <MapControls
          scale={scale}
          scaleRange={scaleRange}
          viewId={viewId}
          onViewChange={onViewChange}
          onZoom={(factor) => controller.current?.zoom(factor)}
          onReset={() => controller.current?.reset()}
        />
      </div>
    </>
  );
}
