import type { BedStatus } from "@/types/ward";

import { type KitModuleId, WARD_KIT } from "./wardKit";

/**
 * 病房版面：只依床數決定欄排數與模組擺放，判定結果、視窗大小都不參與，
 * 所以篩選、選床、縮放都不會重新排床。規則與 scripts/blender/kit/layout.py 一致，修改時兩邊需同步。
 */

/** 地面座標（公尺）：x 向右、z 朝相機（病房前方）。 */
export type FloorPoint = { x: number; z: number };
export type WardGrid = { columns: number; rows: number };
export type ModulePlacement = { moduleId: KitModuleId; origin: FloorPoint };
export type BedSlot = {
  bedCode: string;
  row: number;
  column: number;
  anchor: FloorPoint;
};
export type FloorBounds = { minX: number; maxX: number; maxZ: number };
export type WardLayout = WardGrid & {
  beds: BedSlot[];
  modules: ModulePlacement[];
  bounds: FloorBounds;
};

const { bay, edges, grid, view } = WARD_KIT;

function clampColumns(columns: number): number {
  return Math.min(Math.max(columns, grid.minColumns), grid.maxColumns);
}

/** 在接近目標畫面比例的欄數附近，挑空床位最少者；同數時取較接近理想值者。 */
export function getWardGrid(bedCount: number): WardGrid {
  const slots = Math.max(bedCount, 1);
  const rowScreenRatio =
    (bay.rowPitchM * Math.sin((view.pitchDeg * Math.PI) / 180)) / bay.widthM;
  const ideal = Math.sqrt(slots * grid.targetAspect * rowScreenRatio);
  const cost = (columns: number) => [
    Math.ceil(slots / columns) * columns - slots,
    Math.abs(columns - ideal),
  ];
  const columns = [Math.floor(ideal), Math.ceil(ideal), Math.ceil(ideal) + 1]
    .map(clampColumns)
    .reduce((best, candidate) => {
      const [emptyBest = 0, gapBest = 0] = cost(best);
      const [emptyNext = 0, gapNext = 0] = cost(candidate);
      const isBetter =
        emptyNext < emptyBest || (emptyNext === emptyBest && gapNext < gapBest);
      return isBetter ? candidate : best;
    });
  return { columns, rows: Math.ceil(slots / columns) };
}

function getSideModuleIds(row: number): [KitModuleId, KitModuleId] {
  if (row === 0) return ["sideBackLeft", "sideBackRight"];
  // 第 1 排起兩種擺設交替，長走道才不會每段都一樣
  return row % 2 === 1
    ? ["sideLeft", "sideRight"]
    : ["sideLeftAlt", "sideRightAlt"];
}

function placeBays({ columns, rows }: WardGrid): ModulePlacement[] {
  return Array.from({ length: columns * rows }, (_, index) => {
    const row = Math.floor(index / columns);
    const moduleId: KitModuleId = row === 0 ? "bayBackwall" : "baySpine";
    const origin = {
      x: (index % columns) * bay.widthM,
      z: row * bay.rowPitchM,
    };
    return { moduleId, origin };
  });
}

function placeSides({ columns, rows }: WardGrid): ModulePlacement[] {
  return Array.from({ length: rows }, (_, row) => {
    const [left, right] = getSideModuleIds(row);
    const z = row * bay.rowPitchM;
    return [
      { moduleId: left, origin: { x: -edges.sideWidthM, z } },
      { moduleId: right, origin: { x: columns * bay.widthM, z } },
    ];
  }).flat();
}

function placeFront({ columns, rows }: WardGrid): ModulePlacement[] {
  const z = rows * bay.rowPitchM;
  const fills = Array.from({ length: columns }, (_, column) => ({
    moduleId: "frontFill" as const,
    origin: { x: column * bay.widthM, z },
  }));
  return [
    ...fills,
    { moduleId: "frontLeft", origin: { x: -edges.sideWidthM, z } },
    { moduleId: "frontRight", origin: { x: columns * bay.widthM, z } },
  ];
}

/** 依原始順序由後排往前、每排由左往右放床；DOM 與 Tab 順序也因此與畫面一致。 */
function placeBeds(
  bedCodes: readonly string[],
  { columns }: WardGrid,
): BedSlot[] {
  return bedCodes.map((bedCode, index) => {
    const row = Math.floor(index / columns);
    const column = index % columns;
    const anchor = {
      x: column * bay.widthM + bay.widthM / 2,
      z: row * bay.rowPitchM + bay.bedCenterM,
    };
    return { bedCode, row, column, anchor };
  });
}

export function buildWardLayout(
  beds: readonly Pick<BedStatus, "bedCode">[],
): WardLayout {
  const wardGrid = getWardGrid(beds.length);
  const bounds = {
    minX: -edges.sideWidthM,
    maxX: wardGrid.columns * bay.widthM + edges.sideWidthM,
    maxZ: wardGrid.rows * bay.rowPitchM + edges.frontDepthM,
  };
  return {
    ...wardGrid,
    beds: placeBeds(
      beds.map((bed) => bed.bedCode),
      wardGrid,
    ),
    modules: [
      ...placeBays(wardGrid),
      ...placeSides(wardGrid),
      ...placeFront(wardGrid),
    ],
    bounds,
  };
}
