import { expect, it } from "vitest";

import { WARD_KITS } from "./wardKit";
import { buildWardLayout } from "./wardLayout";
import {
  createWardView,
  type Vec3,
  floorPoint,
  getBedHotspot,
  getMapFrame,
  getSceneCameraPose,
  getSpritePlane,
  projectToMap,
  type WardView,
} from "./wardProjection";

// 正視（yaw 0）與斜視兩個視角都要通過同一組檢查
const FIXTURES = Object.entries(WARD_KITS).map(([id, kit]) => {
  const view = createWardView(kit);
  const layout = buildWardLayout(
    Array.from({ length: 10 }, (_, i) => ({ bedCode: `W-${i}` })),
    kit,
  );
  return { id, kit, view, layout, frame: getMapFrame(view, layout.bounds) };
});

function dot(a: Vec3, b: Vec3) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function offsetOnPlane(
  view: WardView,
  center: Vec3,
  [right, up]: [number, number],
): Vec3 {
  return [0, 1, 2].map(
    (i) =>
      (center[i] ?? 0) + (view.right[i] ?? 0) * right + (view.up[i] ?? 0) * up,
  ) as unknown as Vec3;
}

it.each(FIXTURES)(
  "$id：three.js 相機換算與 DOM 疊層的位置一致（誤差 < 0.5 px）",
  ({ view, frame }) => {
    const camera = { x: -120, y: 45, scale: 1.4 };
    const viewport = { width: 1280, height: 720 };
    const pose = getSceneCameraPose(camera, viewport, frame);
    const point: Vec3 = [3.3, 0.8, 5.1];
    const relative: Vec3 = [
      point[0] - pose.position[0],
      point[1] - pose.position[1],
      point[2] - pose.position[2],
    ];
    const screenX = viewport.width / 2 + dot(relative, view.right) * pose.zoom;
    const screenY = viewport.height / 2 - dot(relative, view.up) * pose.zoom;
    const map = projectToMap(point, frame);
    expect(Math.abs(screenX - (map.x * camera.scale + camera.x))).toBeLessThan(
      0.5,
    );
    expect(Math.abs(screenY - (map.y * camera.scale + camera.y))).toBeLessThan(
      0.5,
    );
  },
);

it.each(FIXTURES)(
  "$id：去背圖平面的床心錨點投影在床心地面上，且最下緣不低於地板",
  ({ kit, view, layout, frame }) => {
    const { sprite } = kit;
    const anchor = layout.beds[3]?.anchor ?? { x: 0, z: 0 };
    const plane = getSpritePlane(anchor, view);
    const toPlane = (px: number, py: number) =>
      offsetOnPlane(view, plane.center, [
        (px / sprite.widthPx - 0.5) * plane.width,
        (0.5 - py / sprite.heightPx) * plane.height,
      ]);
    const onPlane = projectToMap(
      toPlane(sprite.anchorPx.x, sprite.anchorPx.y),
      frame,
    );
    const onFloor = projectToMap(floorPoint(anchor), frame);
    expect(onPlane.x).toBeCloseTo(onFloor.x, 6);
    expect(onPlane.y).toBeCloseTo(onFloor.y, 6);
    const { left, bottom } = sprite.contentRectPx;
    expect(toPlane(left, bottom)[1]).toBeGreaterThanOrEqual(0);
  },
);

it.each(FIXTURES)("$id：相鄰病床的可點範圍互不重疊", ({ layout, frame }) => {
  const rects = layout.beds.map((bed) => getBedHotspot(bed.anchor, frame));
  const overlaps = rects.flatMap((a, i) =>
    rects
      .slice(i + 1)
      .filter(
        (b) =>
          a.x < b.x + b.width &&
          b.x < a.x + a.width &&
          a.y < b.y + b.height &&
          b.y < a.y + a.height,
      ),
  );
  expect(overlaps).toEqual([]);
});

it.each(FIXTURES)(
  "$id：地圖外框包含所有病床可點範圍",
  ({ kit, layout, frame }) => {
    const width = frame.widthM * kit.view.pxPerMeter;
    const height = frame.heightM * kit.view.pxPerMeter;
    const rects = layout.beds.map((bed) => getBedHotspot(bed.anchor, frame));
    expect(
      rects.every(
        (r) =>
          r.x >= 0 &&
          r.y >= 0 &&
          r.x + r.width <= width &&
          r.y + r.height <= height,
      ),
    ).toBe(true);
  },
);
