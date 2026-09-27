/** 地圖互動常數：縮放以預設病床尺寸為 100%，不改動床位順序；最小倍率依視窗動態計算（getScaleRange）。 */
export const MAP_LIMITS = {
  maxScale: 2,
  // 初始視野至少此倍率：窄螢幕完整顯示時病房會縮成一條，改從中央開始，仍可縮到完整顯示
  minInitialScale: 0.5,
  // 判斷是否已到縮放上下限時容許的相對誤差
  scaleTolerance: 0.001,
  dragThresholdPx: 6,
  panStepPx: 64,
  zoomStep: 1.2,
  wheelSensitivity: 0.0015,
  focusPaddingPx: 24,
  // 開詳情卡時病房右緣與大卡的最小間距，與安全區的適配留白（lg 為 2rem）一致
  panelGapPx: 32,
  wheelLinePx: 16,
  maxWheelDeltaPx: 150,
  // 低於此倍率時床號標籤只留圖示與床號，避免相鄰標籤重疊
  compactLabelScale: 0.75,
} as const;

export type MapPoint = { x: number; y: number };
export type MapCamera = MapPoint & { scale: number };
export type MapSize = { width: number; height: number };
/** 地圖視窗內可放病房的區域（px）：扣掉疊在場景上的頂列、側欄等外框；x、y 為左上角。 */
export type MapArea = MapPoint & MapSize;
export type MapBounds = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};
export type ScaleRange = { min: number; max: number };
export const INITIAL_CAMERA: MapCamera = { x: 0, y: 0, scale: 1 };

/** 病床按鈕的 DOM id；關閉大卡後用來把焦點送回原本的病床。 */
export function getBedButtonId(bedCode: string): string {
  return `bed-${bedCode}`;
}

/** 倍率是否已到上下限（容許浮點誤差）；縮放按鈕據此停用。 */
export function getZoomAvailability(scale: number, range: ScaleRange) {
  const tolerance = MAP_LIMITS.scaleTolerance;
  return {
    canZoomOut: scale > range.min * (1 + tolerance),
    canZoomIn: scale < range.max * (1 - tolerance),
  };
}

/** 縮放範圍：最小倍率剛好把整個病房放進可視區域，不能再縮小；床很少時上限不低於下限。 */
export function getScaleRange(area: MapSize, world: MapSize): ScaleRange {
  const min = Math.min(area.width / world.width, area.height / world.height);
  return { min, max: Math.max(MAP_LIMITS.maxScale, min) };
}

function clampScale(scale: number, range: ScaleRange): number {
  return Math.max(range.min, Math.min(range.max, scale));
}

/** 初始視野：以最小倍率完整顯示並置中於可視區域（窄螢幕另有倍率下限）。 */
export function getInitialCamera(area: MapArea, world: MapSize): MapCamera {
  const range = getScaleRange(area, world);
  const scale = clampScale(MAP_LIMITS.minInitialScale, range);
  return {
    scale,
    x: area.x + (area.width - world.width * scale) / 2,
    y: area.y + (area.height - world.height * scale) / 2,
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
  range: ScaleRange,
): MapCamera {
  const scale = clampScale(camera.scale * factor, range);
  const ratio = scale / camera.scale;
  return {
    scale,
    x: anchor.x - (anchor.x - camera.x) * ratio,
    y: anchor.y - (anchor.y - camera.y) * ratio,
  };
}

/** 單軸位移（相對可視區域起點）：病房比區域大時邊緣不能拖進區域，比區域小時置中。 */
function clampAxis(offset: number, area: number, world: number): number {
  const overflow = area - world;
  if (overflow >= 0) return overflow / 2;
  return Math.max(overflow, Math.min(0, offset));
}

/** 可視區域永遠落在病房範圍內（放不滿的軸置中）；外框後方露出的是病房外的地坪。 */
export function clampCamera(
  camera: MapCamera,
  area: MapArea,
  world: MapSize,
  range: ScaleRange,
): MapCamera {
  const scale = clampScale(camera.scale, range);
  return {
    scale,
    x: area.x + clampAxis(camera.x - area.x, area.width, world.width * scale),
    y: area.y + clampAxis(camera.y - area.y, area.height, world.height * scale),
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
