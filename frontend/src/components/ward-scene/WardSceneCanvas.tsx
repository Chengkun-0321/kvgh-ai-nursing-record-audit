"use client";

import { Canvas } from "@react-three/fiber";
import { Suspense, useEffect } from "react";

import { preloadWardView } from "@/lib/sceneAssets";
import type { VerdictFilterValue } from "@/lib/verdict";
import type { CameraChannel } from "@/lib/wardMap";
import type { WardLayout } from "@/lib/wardLayout";
import type { MapFrame } from "@/lib/wardProjection";
import type { BedStatus } from "@/types/ward";

import { BedSpriteLayer } from "./BedSpriteLayer";
import { DeferredMount } from "./DeferredMount";
import { SceneCameraRig } from "./SceneCameraRig";
import { WardKitModules } from "./WardKitModules";
import { WardViewPreloader } from "./WardViewPreloader";

export type WardSceneCanvasProps = {
  beds: readonly BedStatus[];
  layout: WardLayout;
  frame: MapFrame;
  activeFilter: VerdictFilterValue;
  channel: CameraChannel;
};

// 高解析螢幕最多 2 倍，避免大尺寸螢幕上 GPU 負擔過重
const SCENE_DPR: [number, number] = [1, 2];
// 沒有獨立 GPU（例如 VDI）時讓建立失敗，改用 2D 版本
const GL_OPTIONS = {
  antialias: true,
  alpha: true,
  failIfMajorPerformanceCaveat: true,
} as const;
const CAMERA_OPTIONS = {
  near: 1,
  far: 400,
  position: [0, 0, 100] as [number, number, number],
};

/**
 * 病房 3D 場景：模組與床下陰影的光影已在 Blender 算好，這裡只以無光照材質顯示。
 * 視角（正視／斜視）由 frame.view 決定；canvas 透明，病房外露出舞台的地坪底色。
 * `flat` 關閉色調映射、`frameloop="demand"` 只在相機移動或淡化時重繪。
 */
export function WardSceneCanvas({
  beds,
  layout,
  frame,
  activeFilter,
  channel,
}: WardSceneCanvasProps) {
  // GL 初始化期間就開始下載目前視角素材，不必等 R3F 首次渲染
  useEffect(
    () => preloadWardView(frame.view.kit, beds),
    [frame.view.kit, beds],
  );

  return (
    <Canvas
      orthographic
      flat
      frameloop="demand"
      dpr={SCENE_DPR}
      gl={GL_OPTIONS}
      camera={CAMERA_OPTIONS}
      aria-hidden="true"
    >
      <Suspense fallback={null}>
        {/* 素材載入期間不顯示 fallback，就緒即繪製（不受 Suspense 重新顯示的 300ms 節流） */}
        <DeferredMount>
          <WardKitModules layout={layout} kit={frame.view.kit} />
          <BedSpriteLayer
            beds={beds}
            slots={layout.beds}
            view={frame.view}
            activeFilter={activeFilter}
          />
          {/* 放在 Suspense 內最後：R3F 根層 Suspense 在模型載入前會隱藏子樹，放外面時掛載 effect 不會執行 */}
          <SceneCameraRig channel={channel} frame={frame} />
          <WardViewPreloader kit={frame.view.kit} beds={beds} />
        </DeferredMount>
      </Suspense>
    </Canvas>
  );
}
