/** 地圖互動常數：縮放以預設病床尺寸為 100%，不改動床位順序。 */
export const MAP_LIMITS = {
  minScale: 0.5,
  maxScale: 2,
  dragThresholdPx: 6,
  panStepPx: 64,
  zoomStep: 1.2,
  wheelSensitivity: 0.0015,
  edgePaddingPx: 80,
  focusPaddingPx: 24,
  panelGapPx: 40,
  wheelLinePx: 16,
  maxWheelDeltaPx: 150,
  // 低於此倍率時床號標籤只留圖示與床號，避免相鄰標籤重疊
  compactLabelScale: 0.75,
} as const;

export type MapPoint = { x: number; y: number };
export type MapCamera = MapPoint & { scale: number };
export type MapSize = { width: number; height: number };
export type MapBounds = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};
export const INITIAL_CAMERA: MapCamera = { x: 0, y: 0, scale: 1 };

/** 病床按鈕的 DOM id；關閉大卡後用來把焦點送回原本的病床。 */
export function getBedButtonId(bedCode: string): string {
  return `bed-${bedCode}`;
}

/** 初始視野：整個病房放進可用範圍（最多 100%），放得下就置中，放不下就從左上開始。 */
export function getInitialCamera(bounds: MapBounds, world: MapSize): MapCamera {
  const width = bounds.right - bounds.left;
  const height = bounds.bottom - bounds.top;
  const fit = Math.min(width / world.width, height / world.height, 1);
  const scale = Math.max(MAP_LIMITS.minScale, fit);
  return {
    scale,
    x: bounds.left + Math.max(0, (width - world.width * scale) / 2),
    y: bounds.top + Math.max(0, (height - world.height * scale) / 2),
  };
}

export type MapKeyCommand =
  | { type: "pan"; direction: MapPoint }
  | { type: "zoom"; factor: number }
  | { type: "reset" };

const PAN_KEYS: Record<string, MapPoint> = {
  ArrowLeft: { x: 1, y: 0 },
  ArrowRight: { x: -1, y: 0 },
  ArrowUp: { x: 0, y: 1 },
  ArrowDown: { x: 0, y: -1 },
};

const ZOOM_KEYS: Record<string, number> = {
  "+": MAP_LIMITS.zoomStep,
  "=": MAP_LIMITS.zoomStep,
  "-": 1 / MAP_LIMITS.zoomStep,
};

/** 鍵盤對應：方向鍵平移、加減鍵縮放、0／Home 重設。 */
export function getKeyCommand(key: string): MapKeyCommand | undefined {
  const direction = PAN_KEYS[key];
  if (direction) return { type: "pan", direction };
  const factor = ZOOM_KEYS[key];
  if (factor) return { type: "zoom", factor };
  if (key === "0" || key === "Home") return { type: "reset" };
  return undefined;
}

/** 滾輪位移換算縮放倍率；deltaMode 依序為像素、行、頁。 */
export function getWheelZoomFactor(
  deltaY: number,
  deltaMode: number,
  pageHeight: number,
): number {
  const unit = [1, MAP_LIMITS.wheelLinePx, pageHeight][deltaMode] ?? 1;
  const delta = Math.max(
    -MAP_LIMITS.maxWheelDeltaPx,
    Math.min(MAP_LIMITS.maxWheelDeltaPx, deltaY * unit),
  );
  return Math.exp(-delta * MAP_LIMITS.wheelSensitivity);
}

export type CameraChannel = {
  publish: (camera: MapCamera) => void;
  subscribe: (listener: (camera: MapCamera) => void) => () => void;
  getCurrent: () => MapCamera;
};

/** 地圖控制器與 3D 相機之間的同步通道；不經 React state，平移時不會重新渲染元件。 */
export function createCameraChannel(): CameraChannel {
  let current = INITIAL_CAMERA;
  const listeners = new Set<(camera: MapCamera) => void>();
  return {
    publish(camera) {
      current = camera;
      listeners.forEach((listener) => listener(camera));
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    getCurrent: () => current,
  };
}

/** 游標下的世界座標維持不動，避免放大時視線跳到畫布中央。 */
export function zoomAt(
  camera: MapCamera,
  anchor: MapPoint,
  factor: number,
): MapCamera {
  const scale = Math.max(
    MAP_LIMITS.minScale,
    Math.min(MAP_LIMITS.maxScale, camera.scale * factor),
  );
  const ratio = scale / camera.scale;
  return {
    scale,
    x: anchor.x - (anchor.x - camera.x) * ratio,
    y: anchor.y - (anchor.y - camera.y) * ratio,
  };
}

/** 保留少量可拖曳邊界，但不允許把整個病房拖出視窗。 */
export function clampCamera(
  camera: MapCamera,
  viewport: MapSize,
  world: MapSize,
): MapCamera {
  const pad = MAP_LIMITS.edgePaddingPx;
  return {
    ...camera,
    x: Math.max(
      Math.min(0, viewport.width - world.width * camera.scale) - pad,
      Math.min(pad, camera.x),
    ),
    y: Math.max(
      Math.min(0, viewport.height - world.height * camera.scale) - pad,
      Math.min(pad, camera.y),
    ),
  };
}

/** 只平移到可視範圍，不因選床或鍵盤焦點重新排版。 */
export function getRevealOffset(
  start: number,
  end: number,
  minimum: number,
  maximum: number,
): number {
  if (end - start > maximum - minimum) return minimum - start;
  if (start < minimum) return minimum - start;
  if (end > maximum) return maximum - end;
  return 0;
}

/** 雙指中點與距離共用同一座標系，移動中點時同時平移。 */
export function getPointerPair(points: MapPoint[]) {
  const [first, second] = points;
  if (!first || !second) return undefined;
  return {
    center: { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 },
    distance: Math.max(1, Math.hypot(first.x - second.x, first.y - second.y)),
  };
}
