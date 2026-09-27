"""結構件：樓板、牆段、剖面收邊。

娃娃屋剖面的切口（牆頂、樓板側面、外牆面）一律用灰色，與室內暖色區隔，貼近概念圖。
"""

import bpy

from ..geometry import box
from . import part

SLAB_THICKNESS_M = 0.3
FLOOR_FINISH_M = 0.02
CAP_THICKNESS_M = 0.03
OUTER_SKIN_M = 0.03


def floor_slab(col: bpy.types.Collection, size_m: tuple, slab_m: float = SLAB_THICKNESS_M) -> list:
    """上層地磚面加下層灰色樓板，前緣與右緣剖面才看得出切口；slab_m 為 0 時只建地磚面。"""
    width_m, depth_m = size_m
    objects = [box("floor", (0, -FLOOR_FINISH_M, 0), (width_m, 0, depth_m), part(col, "floor"))]
    if slab_m > FLOOR_FINISH_M:
        objects.append(box("slab", (0, -slab_m, 0), (width_m, -FLOOR_FINISH_M, depth_m), part(col, "wallOuter")))
    return objects


def wall(col: bpy.types.Collection, lo: tuple, hi: tuple) -> list:
    """牆身（室內色）加頂端灰色剖面收邊。"""
    body = box("wall", lo, (hi[0], hi[1] - CAP_THICKNESS_M, hi[2]), part(col, "wall"))
    cap = box("wall_cap", (lo[0], hi[1] - CAP_THICKNESS_M, lo[2]), hi, part(col, "wallCap"))
    return [body, cap]


def outer_skin_x(col: bpy.types.Collection, x: float, height_m: float, depth_m: float) -> list:
    """朝 +X 的外牆面（右側牆外側會被相機看到），貼一層灰色。"""
    return [box("wall_outer", (x, -SLAB_THICKNESS_M, 0), (x + OUTER_SKIN_M, height_m, depth_m), part(col, "wallOuter"))]


def outer_skin_z(col: bpy.types.Collection, x_range: tuple, height_m: float, face_z: float) -> list:
    """朝 +Z 的剖面牆外側（正視角的前緣矮牆），貼一層灰色。"""
    lo, hi = (x_range[0], 0, face_z), (x_range[1], height_m, face_z + OUTER_SKIN_M)
    return [box("wall_outer", lo, hi, part(col, "wallOuter"))]


def end_cap_z(col: bpy.types.Collection, x_range: tuple, height_m: float, face_z: float) -> list:
    """牆在前緣被剖開的端面（朝相機），用灰色表示切口。"""
    lo, hi = (x_range[0], 0, face_z), (x_range[1], height_m, face_z + 0.005)
    return [box("wall_end", lo, hi, part(col, "wallCap"))]


def baseboard(col: bpy.types.Collection, lo: tuple, hi: tuple) -> list:
    """踢腳板，讓牆與地板交界更有層次。"""
    return [box("baseboard", lo, hi, part(col, "wallShade"))]
