"""病房版面（Blender 預覽用）；規則與前端 lib/wardLayout.ts 一致，改動時兩邊需同步。

欄數只看床數：在接近 targetAspect 的欄數附近，挑空床位最少者（同數取較接近理想值者）。
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Placement:
    """模組擺放：origin 為模組左後角的地面座標（前端 x、z，公尺）。"""

    module_id: str
    x: float
    z: float


def ward_grid(bed_count: int, kit: dict) -> tuple[int, int]:
    """回傳 (欄數, 排數)。"""
    slots = max(bed_count, 1)
    bay, grid = kit["bay"], kit["grid"]
    row_screen_ratio = bay["rowPitchM"] * math.sin(math.radians(kit["view"]["pitchDeg"])) / bay["widthM"]
    ideal = math.sqrt(slots * grid["targetAspect"] * row_screen_ratio)
    candidates = {min(max(c, grid["minColumns"]), grid["maxColumns"]) for c in (math.floor(ideal), math.ceil(ideal), math.ceil(ideal) + 1)}
    columns = min(candidates, key=lambda c: (math.ceil(slots / c) * c - slots, abs(c - ideal)))
    return columns, math.ceil(slots / columns)


def _side_ids(row: int) -> tuple[str, str]:
    if row == 0:
        return "sideBackLeft", "sideBackRight"
    # 第 1 排起兩種擺設交替，長走道才不會每段都一樣
    suffix = "" if row % 2 == 1 else "Alt"
    return f"sideLeft{suffix}", f"sideRight{suffix}"


def module_placements(columns: int, rows: int, kit: dict) -> list[Placement]:
    """床位、左右走道與前緣模組的擺放清單。"""
    width, pitch, side = kit["bay"]["widthM"], kit["bay"]["rowPitchM"], kit["edges"]["sideWidthM"]
    placements = []
    for index in range(columns * rows):
        row, column = divmod(index, columns)
        placements.append(Placement("bayBackwall" if row == 0 else "baySpine", column * width, row * pitch))
    for row in range(rows):
        left, right = _side_ids(row)
        placements += [Placement(left, -side, row * pitch), Placement(right, columns * width, row * pitch)]
    front_z = rows * pitch
    placements += [Placement("frontFill", column * width, front_z) for column in range(columns)]
    return placements + [Placement("frontLeft", -side, front_z), Placement("frontRight", columns * width, front_z)]


def bed_anchors(bed_count: int, columns: int, kit: dict) -> list[tuple[float, float]]:
    """每床床心的地面座標；由後排往前、每排由左往右。"""
    bay = kit["bay"]
    return [
        ((i % columns) * bay["widthM"] + bay["widthM"] / 2, (i // columns) * bay["rowPitchM"] + bay["bedCenterM"])
        for i in range(bed_count)
    ]


def scene_bounds(columns: int, rows: int, kit: dict) -> list[tuple[float, float, float]]:
    """場景外框 8 個角點（含牆高與樓板厚），用於相機取景。"""
    side, edges = kit["edges"]["sideWidthM"], kit["edges"]
    x0, x1 = -side, columns * kit["bay"]["widthM"] + side
    z1 = rows * kit["bay"]["rowPitchM"] + edges["frontDepthM"]
    y0, y1 = -edges["slabDepthM"], kit["bay"]["backWallHeightM"]
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (0.0, z1)]
