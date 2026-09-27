"""床邊家具：床頭櫃、陪病椅。"""

import bpy

from ..geometry import CylinderSpec, box, cylinder, rotate_about_y
from . import part

CABINET_W, CABINET_D, CABINET_H = 0.46, 0.45, 0.78
SEAT_W, SEAT_Y = 0.5, 0.45


def bedside_cabinet(col: bpy.types.Collection, x: float, z: float) -> list:
    """(x, z) 為櫃子左後角；白色櫃體、木紋檯面、兩個抽屜。"""
    x1, z1 = x + CABINET_W, z + CABINET_D
    objects = [
        box("cabinet_body", (x, 0.06, z), (x1, CABINET_H - 0.03, z1), part(col, "wood", 0.012)),
        box("cabinet_top", (x - 0.01, CABINET_H - 0.03, z - 0.01), (x1 + 0.01, CABINET_H, z1 + 0.01), part(col, "woodTop", 0.008)),
        box("cabinet_plinth", (x + 0.02, 0, z + 0.02), (x1 - 0.02, 0.06, z1 - 0.02), part(col, "metalDark")),
    ]
    for index, y in enumerate((0.58, 0.36)):
        objects.append(box(f"drawer_gap_{index}", (x + 0.02, y, z1), (x1 - 0.02, y + 0.008, z1 + 0.003), part(col, "woodDark")))
        objects.append(box(f"drawer_handle_{index}", (x + 0.17, y + 0.08, z1), (x1 - 0.17, y + 0.1, z1 + 0.02), part(col, "metal")))
    return objects + _cabinet_items(col, x, z)


def _cabinet_items(col: bpy.types.Collection, x: float, z: float) -> list:
    """檯面小物（水瓶、面紙盒），讓床邊更有生活感。"""
    return [
        cylinder("water_bottle", CylinderSpec((x + 0.12, CABINET_H, z + 0.25), 0.035, 0.22), part(col, "window")),
        cylinder("bottle_cap", CylinderSpec((x + 0.12, CABINET_H + 0.22, z + 0.25), 0.02, 0.03), part(col, "screenLine")),
        box("tissue_box", (x + 0.22, CABINET_H, z + 0.12), (x + 0.4, CABINET_H + 0.09, z + 0.3), part(col, "panel", 0.008)),
    ]


def visitor_chair(col: bpy.types.Collection, x: float, z: float, facing_deg: float) -> list:
    """(x, z) 為座面中心；facing_deg 為繞垂直軸旋轉角度（負值朝左）。"""
    half = SEAT_W / 2
    objects = [
        box("chair_seat", (x - half, SEAT_Y - 0.08, z - half), (x + half, SEAT_Y, z + half), part(col, "fabric", 0.03)),
        box("chair_back", (x - half, SEAT_Y, z - half), (x + half, SEAT_Y + 0.42, z - half + 0.08), part(col, "fabric", 0.03)),
        box("chair_arm_l", (x - half - 0.04, SEAT_Y, z - half + 0.05), (x - half, SEAT_Y + 0.2, z + half - 0.05), part(col, "woodDark", 0.01)),
        box("chair_arm_r", (x + half, SEAT_Y, z - half + 0.05), (x + half + 0.04, SEAT_Y + 0.2, z + half - 0.05), part(col, "woodDark", 0.01)),
    ]
    for index, (dx, dz) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        lx, lz = x + dx * (half - 0.04), z + dz * (half - 0.04)
        objects.append(box(f"chair_leg_{index}", (lx - 0.02, 0, lz - 0.02), (lx + 0.02, SEAT_Y - 0.08, lz + 0.02), part(col, "metalDark")))
    rotate_about_y(objects, (x, 0, z), facing_deg)
    return objects
