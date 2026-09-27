"""床頭牆：深色木飾板、設備帶（醫療氣體出口、閱讀燈）。"""

import bpy

from ..geometry import CylinderSpec, box, cylinder
from . import part

RAIL_HEIGHT_M = 0.26
RAIL_DEPTH_M = 0.07
ACCENT_DEPTH_M = 0.025
GROOVE_PITCH_M = 0.13
# 相對於設備帶中心的出口位置（公尺）與材質
OUTLETS = ((-0.62, "metal"), (-0.5, "screenLine"), (-0.38, "metalDark"), (0.38, "metal"), (0.5, "metalDark"), (0.62, "metal"))


def wood_accent(col: bpy.types.Collection, x_range: tuple, y_range: tuple, face_z: float) -> list:
    """床頭後方的深色直紋木飾板。"""
    (x0, x1), (y0, y1) = x_range, y_range
    objects = [box("accent_panel", (x0, y0, face_z), (x1, y1, face_z + ACCENT_DEPTH_M), part(col, "woodDark"))]
    x = x0 + GROOVE_PITCH_M
    while x < x1 - 0.05:
        objects.append(box("accent_groove", (x - 0.006, y0, face_z + ACCENT_DEPTH_M), (x + 0.006, y1, face_z + ACCENT_DEPTH_M + 0.003), part(col, "wood")))
        x += GROOVE_PITCH_M
    return objects


def headwall_rail(col: bpy.types.Collection, x_range: tuple, center_y: float, face_z: float) -> list:
    """設備帶；x_range 為左右端點，face_z 為所貼牆面。"""
    y0, y1 = center_y - RAIL_HEIGHT_M / 2, center_y + RAIL_HEIGHT_M / 2
    mid_x, front_z = (x_range[0] + x_range[1]) / 2, face_z + RAIL_DEPTH_M
    objects = [
        box("headwall_rail", (x_range[0], y0, face_z), (x_range[1], y1, front_z), part(col, "panel", 0.012)),
        box("headwall_trim", (x_range[0], y0 - 0.025, face_z), (x_range[1], y0, front_z + 0.005), part(col, "panelShade")),
        box("reading_lamp", (mid_x - 0.22, y1 - 0.05, front_z), (mid_x + 0.22, y1 - 0.02, front_z + 0.01), part(col, "lamp")),
    ]
    for index, (dx, key) in enumerate(OUTLETS):
        spec = CylinderSpec((mid_x + dx, center_y - 0.03, front_z), 0.028, 0.025, "z")
        objects.append(cylinder(f"outlet_{index}", spec, part(col, key)))
    return objects
