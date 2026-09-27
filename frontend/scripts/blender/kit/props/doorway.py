"""側牆上的病房門（內側牆面，面向 +X）。"""

import bpy

from ..geometry import box
from . import part

DOOR_HEIGHT_M = 2.1


def ward_door(col: bpy.types.Collection, face_x: float, z_range: tuple) -> list:
    """face_x 為牆內側面；z_range 為門寬範圍。"""
    z0, z1 = z_range
    return [
        box("door_frame", (face_x, 0, z0 - 0.06), (face_x + 0.03, DOOR_HEIGHT_M + 0.06, z1 + 0.06), part(col, "wallCap")),
        box("door_leaf", (face_x + 0.03, 0.01, z0), (face_x + 0.06, DOOR_HEIGHT_M, z1), part(col, "wood", 0.005)),
        box("door_vision", (face_x + 0.06, 1.3, z0 + 0.15), (face_x + 0.065, 1.75, z0 + 0.35), part(col, "window")),
        box("door_handle", (face_x + 0.06, 1.0, z1 - 0.18), (face_x + 0.1, 1.03, z1 - 0.06), part(col, "metal")),
        box("door_kick", (face_x + 0.06, 0.01, z0 + 0.02), (face_x + 0.065, 0.25, z1 - 0.02), part(col, "metal")),
    ]
