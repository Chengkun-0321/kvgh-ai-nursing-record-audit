"use client";

import { lazy, Suspense } from "react";

import { DeferredMount } from "./DeferredMount";
import type { WardSceneCanvasProps } from "./WardSceneCanvas";
import { WardSceneErrorBoundary } from "./WardSceneErrorBoundary";

// three.js 拆成獨立 chunk，不影響首頁主程式大小；本元件只在水合後且支援 WebGL 時渲染，伺服器端不會載入
const WardSceneCanvas = lazy(() =>
  import("./WardSceneCanvas").then((mod) => ({ default: mod.WardSceneCanvas })),
);

type WardSceneProps = WardSceneCanvasProps & {
  onError: () => void;
};

/** 地圖底層的 3D 場景；不接收指標事件，互動全部由上層 DOM 地圖處理。 */
export function WardScene({ onError, ...canvasProps }: WardSceneProps) {
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true">
      <WardSceneErrorBoundary onError={onError}>
        <Suspense fallback={null}>
          <DeferredMount>
            <WardSceneCanvas {...canvasProps} />
          </DeferredMount>
        </Suspense>
      </WardSceneErrorBoundary>
    </div>
  );
}
