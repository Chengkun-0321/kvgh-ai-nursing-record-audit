import { WARD_KIT } from "./wardKit";
import type { FloorBounds, FloorPoint } from "./wardLayout";
import type { MapCamera, MapPoint, MapSize } from "./wardMap";

/**
 * 固定視角的正交投影：與 scripts/blender/kit/view.py 使用同一組公式。
 * 世界座標（公尺）：X 向右、Y 向上、+Z 朝相機；地圖座標（px，100% 縮放）：左上為原點、y 向下。
 * 本檔不 import three，可在主程式與單元測試共用。
 */

export type Vec3 = readonly [number, number, number];
export type MapRect = MapPoint & MapSize;
/** 場景外框投影到相機平面後的範圍（公尺）：u 向右、v 向上。 */
export type MapFrame = {
  uMin: number;
  vMax: number;
  widthM: number;
  heightM: number;
};
export type SpritePlane = { center: Vec3; width: number; height: number };
export type CameraPose = { position: Vec3; zoom: number };

const { view, sprite, bay, edges } = WARD_KIT;
const DEG = Math.PI / 180;
const YAW = view.yawDeg * DEG;
const PITCH = view.pitchDeg * DEG;
// 正交相機的距離不影響畫面，只需大於場景深度
const CAMERA_DISTANCE_M = 100;
// 去背圖平面再往相機拉 2 cm，避免與地板深度相同而閃爍
const DEPTH_EPSILON_M = 0.02;

export const VIEW_RIGHT: Vec3 = [Math.cos(YAW), 0, -Math.sin(YAW)];
export const VIEW_UP: Vec3 = [
  -Math.sin(YAW) * Math.sin(PITCH),
  Math.cos(PITCH),
  -Math.cos(YAW) * Math.sin(PITCH),
];
export const VIEW_FORWARD: Vec3 = [
  -Math.sin(YAW) * Math.cos(PITCH),
  -Math.sin(PITCH),
  -Math.cos(YAW) * Math.cos(PITCH),
];
/** three.js 相機與去背圖平面共用的旋轉（Euler，順序 YXZ）。 */
export const VIEW_ROTATION = { x: -PITCH, y: YAW, z: 0, order: "YXZ" } as const;

/** 去背圖 1 px 在 100% 地圖上的長度（px）。 */
const SPRITE_PX_TO_MAP =
  (sprite.planeWidthM / sprite.widthPx) * view.pxPerMeter;

function dot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

/** 向量線性組合：Σ vector × weight。 */
function combine(...terms: [Vec3, number][]): Vec3 {
  return terms.reduce<Vec3>(
    (sum, [vector, weight]) => [
      sum[0] + vector[0] * weight,
      sum[1] + vector[1] * weight,
      sum[2] + vector[2] * weight,
    ],
    [0, 0, 0],
  );
}

export function floorPoint({ x, z }: FloorPoint, y = 0): Vec3 {
  return [x, y, z];
}

/** 場景外框 8 個角點（含牆高與樓板厚）投影後的範圍。 */
export function getMapFrame(bounds: FloorBounds): MapFrame {
  const corners = [bounds.minX, bounds.maxX].flatMap((x) =>
    [-edges.slabDepthM, bay.backWallHeightM].flatMap((y) =>
      [0, bounds.maxZ].map((z): Vec3 => [x, y, z]),
    ),
  );
  const us = corners.map((corner) => dot(corner, VIEW_RIGHT));
  const vs = corners.map((corner) => dot(corner, VIEW_UP));
  const uMin = Math.min(...us);
  const vMax = Math.max(...vs);
  return {
    uMin,
    vMax,
    widthM: Math.max(...us) - uMin,
    heightM: vMax - Math.min(...vs),
  };
}

export function getMapSize(frame: MapFrame): MapSize {
  return {
    width: frame.widthM * view.pxPerMeter,
    height: frame.heightM * view.pxPerMeter,
  };
}

export function projectToMap(point: Vec3, frame: MapFrame): MapPoint {
  return {
    x: (dot(point, VIEW_RIGHT) - frame.uMin) * view.pxPerMeter,
    y: (frame.vMax - dot(point, VIEW_UP)) * view.pxPerMeter,
  };
}

/** 去背圖上某像素落在地圖上的位置：床心錨點對齊床心在地面的投影。 */
function spritePixelToMap(
  anchor: FloorPoint,
  pixel: MapPoint,
  frame: MapFrame,
): MapPoint {
  const origin = projectToMap(floorPoint(anchor), frame);
  return {
    x: origin.x + (pixel.x - sprite.anchorPx.x) * SPRITE_PX_TO_MAP,
    y: origin.y + (pixel.y - sprite.anchorPx.y) * SPRITE_PX_TO_MAP,
  };
}

/** 病床可點範圍：去背圖有內容的矩形。 */
export function getBedHotspot(anchor: FloorPoint, frame: MapFrame): MapRect {
  const { left, top, right, bottom } = sprite.contentRectPx;
  const topLeft = spritePixelToMap(anchor, { x: left, y: top }, frame);
  return {
    ...topLeft,
    width: (right - left) * SPRITE_PX_TO_MAP,
    height: (bottom - top) * SPRITE_PX_TO_MAP,
  };
}

/** 床號標籤位置（床頭上方）。 */
export function getBedLabelPoint(
  anchor: FloorPoint,
  frame: MapFrame,
): MapPoint {
  return spritePixelToMap(anchor, sprite.labelAnchorPx, frame);
}

/** 去背圖平面：正對相機，沿視線前移到圖片最下緣不低於地板。 */
export function getSpritePlane(anchor: FloorPoint): SpritePlane {
  const width = sprite.planeWidthM;
  const height = (width * sprite.heightPx) / sprite.widthPx;
  const belowAnchorM =
    (height * (sprite.contentRectPx.bottom - sprite.anchorPx.y)) /
    sprite.heightPx;
  const lift = belowAnchorM / Math.tan(PITCH) + DEPTH_EPSILON_M;
  const center = combine(
    [floorPoint(anchor), 1],
    [VIEW_FORWARD, -lift],
    [VIEW_RIGHT, -(sprite.anchorPx.x / sprite.widthPx - 0.5) * width],
    [VIEW_UP, -(0.5 - sprite.anchorPx.y / sprite.heightPx) * height],
  );
  return { center, width, height };
}

/**
 * 由地圖相機（DOM 疊層的 translate + scale）換算 three.js 正交相機：
 * 視窗中心對應的地圖點 → 相機平面上的點 → 沿視線往後退。
 */
export function getSceneCameraPose(
  camera: MapCamera,
  viewport: MapSize,
  frame: MapFrame,
): CameraPose {
  const mapX = (viewport.width / 2 - camera.x) / camera.scale;
  const mapY = (viewport.height / 2 - camera.y) / camera.scale;
  const u = frame.uMin + mapX / view.pxPerMeter;
  const v = frame.vMax - mapY / view.pxPerMeter;
  const position = combine(
    [VIEW_RIGHT, u],
    [VIEW_UP, v],
    [VIEW_FORWARD, -CAMERA_DISTANCE_M],
  );
  return { position, zoom: view.pxPerMeter * camera.scale };
}
