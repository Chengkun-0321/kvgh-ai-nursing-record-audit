"""左右側走道模組。

左側牆做全高：相機略朝左看，高牆投影落在病房外，不會遮到床。
右側牆只做矮牆：全高會往左投影蓋住最右欄病床；矮牆外側會被看到，貼灰色外牆面。
"""

import bpy

from ..props import structure
from ..props.carts import linen_cart, medication_cart, wheelchair
from ..props.curtain import privacy_curtain
from ..props.doorway import ward_door
from ..props.fixtures import sanitizer_stand, sink_counter

WALL_THICKNESS_M = 0.15


def _left_wall(col: bpy.types.Collection, kit: dict, depth: float) -> list:
    return structure.wall(col, (0, 0, 0), (WALL_THICKNESS_M, kit["bay"]["backWallHeightM"], depth))


def _right_wall(col: bpy.types.Collection, kit: dict, depth: float) -> list:
    width, height = kit["edges"]["sideWidthM"], kit["edges"]["sideWallHeightM"]
    inner = structure.wall(col, (width - WALL_THICKNESS_M, 0, 0), (width, height, depth))
    return inner + structure.outer_skin_x(col, width, height, depth)


def _back_wall(col: bpy.types.Collection, kit: dict, side: str) -> list:
    width, bay = kit["edges"]["sideWidthM"], kit["bay"]
    objects = structure.wall(col, (0, 0, 0), (width, bay["backWallHeightM"], bay["wallThicknessM"]))
    if side == "right":
        # 後牆右端在高於矮牆的部分是剖面，用灰色表示
        objects += structure.outer_skin_x(col, width, bay["backWallHeightM"], bay["wallThicknessM"])
    return objects


def build_side(col: bpy.types.Collection, kit: dict, side: str, variant: str) -> list:
    """side 為 left／right；variant 為 back（第 0 排，含後牆）、base 或 alt（輪替擺設）。"""
    width, depth = kit["edges"]["sideWidthM"], kit["bay"]["rowPitchM"]
    face_z = kit["bay"]["wallThicknessM"]
    objects = structure.floor_slab(col, width, depth)
    objects += _left_wall(col, kit, depth) if side == "left" else _right_wall(col, kit, depth)
    if variant == "back":
        objects += _back_wall(col, kit, side)
    if side == "right":
        # 最右欄床位的右側隔簾放在本模組左緣
        top = 2.35 if variant == "back" else 1.8
        objects += privacy_curtain(col, 0.04, (face_z + 0.05, face_z + 1.4), top)
    return objects + _side_props(col, side, variant)


def _side_props(col: bpy.types.Collection, side: str, variant: str) -> list:
    """依左右與輪替變體放道具，讓長走道不會每段都一樣。"""
    if side == "left":
        if variant == "alt":
            return ward_door(col, WALL_THICKNESS_M, (1.2, 2.2)) + medication_cart(col, 0.5, 2.9)
        return sanitizer_stand(col, 0.6, 2.4) + linen_cart(col, 0.45, 0.5)
    if variant == "alt":
        return linen_cart(col, 0.7, 1.9) + wheelchair(col, 0.9, 3.3, -30)
    return sink_counter(col, (1.05, 1.62), (1.6, 2.4))
