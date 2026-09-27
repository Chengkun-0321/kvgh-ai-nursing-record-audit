"""後牆的窗（半降百葉）與牆頂燈帶。"""

import bpy

from ..geometry import box
from . import part

FRAME_M = 0.04
SLAT_PITCH_M = 0.045
BLIND_RATIO = 0.55


def blind_window(col: bpy.types.Collection, x_range: tuple, y_range: tuple, face_z: float) -> list:
    """窗面凸出牆面 2 cm；上半部百葉放下，下半部透出窗外光。"""
    (x0, x1), (y0, y1) = x_range, y_range
    objects = [
        box("window_frame", (x0 - FRAME_M, y0 - FRAME_M, face_z), (x1 + FRAME_M, y1 + FRAME_M, face_z + 0.02), part(col, "wallCap")),
        box("window_glass", (x0, y0, face_z + 0.02), (x1, y1, face_z + 0.022), part(col, "window")),
        box("window_sill", (x0 - 0.08, y0 - FRAME_M - 0.03, face_z), (x1 + 0.08, y0 - FRAME_M, face_z + 0.08), part(col, "wallCap", 0.005)),
    ]
    blind_bottom = y1 - (y1 - y0) * BLIND_RATIO
    y = y1 - SLAT_PITCH_M
    while y > blind_bottom:
        objects.append(box("blind_slat", (x0, y, face_z + 0.024), (x1, y + SLAT_PITCH_M * 0.8, face_z + 0.03), part(col, "windowShade")))
        y -= SLAT_PITCH_M
    return objects


def light_strip(col: bpy.types.Collection, x_range: tuple, top_y: float, face_z: float) -> list:
    """牆頂間接照明燈帶。"""
    body = box("light_housing", (x_range[0], top_y - 0.1, face_z), (x_range[1], top_y, face_z + 0.08), part(col, "panel"))
    glow = box("light_glow", (x_range[0], top_y - 0.1, face_z + 0.08), (x_range[1], top_y - 0.04, face_z + 0.085), part(col, "lamp"))
    return [body, glow]
