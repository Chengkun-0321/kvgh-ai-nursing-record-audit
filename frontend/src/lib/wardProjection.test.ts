import { expect, it } from "vitest";

import { WARD_KIT } from "./wardKit";
import { buildWardLayout } from "./wardLayout";
import {
  VIEW_RIGHT,
  VIEW_UP,
  type Vec3,
  floorPoint,
  getBedHotspot,
  getMapFrame,
  getSceneCameraPose,
  getSpritePlane,
  projectToMap,
} from "./wardProjection";

const { sprite } = WARD_KIT;
const layout = buildWardLayout(
  Array.from({ length: 10 }, (_, i) => ({ bedCode: `W-${i}` })),
);
const frame = getMapFrame(layout.bounds);

function dot(a: Vec3, b: Vec3) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function offsetOnPlane(center: Vec3, right: number, up: number): Vec3 {
  return [0, 1, 2].map(
    (i) =>
      (center[i] ?? 0) + (VIEW_RIGHT[i] ?? 0) * right + (VIEW_UP[i] ?? 0) * up,
  ) as unknown as Vec3;
}

it("three.js 相機換算與 DOM 疊層的位置一致（誤差 < 0.5 px）", () => {
  const camera = { x: -120, y: 45, scale: 1.4 };
  const viewport = { width: 1280, height: 720 };
  const pose = getSceneCameraPose(camera, viewport, frame);
  const point: Vec3 = [3.3, 0.8, 5.1];
  const relative: Vec3 = [
    point[0] - pose.position[0],
    point[1] - pose.position[1],
    point[2] - pose.position[2],
  ];
  const screen = {
    x: viewport.width / 2 + dot(relative, VIEW_RIGHT) * pose.zoom,
    y: viewport.height / 2 - dot(relative, VIEW_UP) * pose.zoom,
  };
  const map = projectToMap(point, frame);
  expect(Math.abs(screen.x - (map.x * camera.scale + camera.x))).toBeLessThan(
    0.5,
  );
  expect(Math.abs(screen.y - (map.y * camera.scale + camera.y))).toBeLessThan(
    0.5,
  );
});

it("去背圖平面：床心錨點投影在床心地面上，且最下緣不低於地板", () => {
  const anchor = layout.beds[3]?.anchor ?? { x: 0, z: 0 };
  const plane = getSpritePlane(anchor);
  const toPlane = (px: number, py: number) =>
    offsetOnPlane(
      plane.center,
      (px / sprite.widthPx - 0.5) * plane.width,
      (0.5 - py / sprite.heightPx) * plane.height,
    );
  const anchorOnPlane = projectToMap(
    toPlane(sprite.anchorPx.x, sprite.anchorPx.y),
    frame,
  );
  const anchorOnFloor = projectToMap(floorPoint(anchor), frame);
  expect(anchorOnPlane.x).toBeCloseTo(anchorOnFloor.x, 6);
  expect(anchorOnPlane.y).toBeCloseTo(anchorOnFloor.y, 6);
  expect(
    toPlane(sprite.contentRectPx.left, sprite.contentRectPx.bottom)[1],
  ).toBeGreaterThanOrEqual(0);
});

it("相鄰病床的可點範圍互不重疊", () => {
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

it("地圖外框包含所有病床可點範圍", () => {
  const { width, height } = {
    width: frame.widthM * WARD_KIT.view.pxPerMeter,
    height: frame.heightM * WARD_KIT.view.pxPerMeter,
  };
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
});
