import { useState, useSyncExternalStore } from "react";

export type WebGLSupport = "pending" | "supported" | "unsupported";

let cachedSupport: WebGLSupport | undefined;

function detectWebGL(): WebGLSupport {
  // 開發時可用 ?scene=2d 強制檢查 2D 版本
  if (new URLSearchParams(window.location.search).get("scene") === "2d")
    return "unsupported";
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("webgl2", {
    failIfMajorPerformanceCaveat: true,
  });
  return context ? "supported" : "unsupported";
}

function getSnapshot(): WebGLSupport {
  cachedSupport ??= detectWebGL();
  return cachedSupport;
}

const subscribe = () => () => {};

/** 伺服器端與水合前回傳 pending；之後依瀏覽器能力決定 3D 或 2D 病房。 */
export function useWebGLSupport(): WebGLSupport {
  return useSyncExternalStore(subscribe, getSnapshot, () => "pending");
}

export type WardSceneMode = "pending" | "3d" | "2d";

function getSceneMode(support: WebGLSupport, hasError: boolean): WardSceneMode {
  if (hasError || support === "unsupported") return "2d";
  return support === "supported" ? "3d" : "pending";
}

/** 病房呈現方式：支援 WebGL 用 3D 場景；不支援或場景載入失敗時改用 2D 清單。 */
export function useWardSceneMode() {
  const support = useWebGLSupport();
  const [hasError, setHasError] = useState(false);
  return {
    mode: getSceneMode(support, hasError),
    reportSceneError: () => setHasError(true),
  };
}
