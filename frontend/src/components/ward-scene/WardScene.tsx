"use client";

import dynamic from "next/dynamic";

import type { WardSceneCanvasProps } from "./WardSceneCanvas";
import { WardSceneErrorBoundary } from "./WardSceneErrorBoundary";

// three.js 只在瀏覽器執行，並拆成獨立 chunk，不影響首頁主程式大小
const WardSceneCanvas = dynamic(
  () => import("./WardSceneCanvas").then((mod) => mod.WardSceneCanvas),
  { ssr: false },
);

type WardSceneProps = WardSceneCanvasProps & {
  onError: () => void;
};

/** 地圖底層的 3D 場景；不接收指標事件，互動全部由上層 DOM 地圖處理。 */
export function WardScene({ onError, ...canvasProps }: WardSceneProps) {
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true">
      <WardSceneErrorBoundary onError={onError}>
        <WardSceneCanvas {...canvasProps} />
      </WardSceneErrorBoundary>
    </div>
  );
}
