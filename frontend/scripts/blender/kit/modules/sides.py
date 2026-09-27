"""左右側走道模組。

斜視角（style＝leftLook）：
- 左側牆做全高：相機略朝左看，高牆投影落在病房外，不會遮到床。
- 右側牆只做矮牆：全高會往左投影蓋住最右欄病床；矮牆外側會被看到，貼灰色外牆面。

正視角（style＝symmetric）：側牆正對相機的側面看不到，左右都做矮牆（只看得到牆頂），
道具依較淺的走道與排距重新擺放，不做左牆的門。
"""

import bpy

from ..props import structure
from ..props.carts import linen_cart, medication_cart, wheelchair
from ..props.curtain import privacy_curtain
from ..props.doorway import ward_door
from ..props.fixtures import sanitizer_stand, sink_counter
from .bay import curtain_depth

WALL_THICKNESS_M = 0.15
SINK_DEPTH_M = 0.57


def _left_wall(col: bpy.types.Collection, kit: dict, depth: float) -> list:
    if kit["style"] == "symmetric":
        return structure.wall(col, (0, 0, 0), (WALL_THICKNESS_M, kit["edges"]["sideWallHeightM"], depth))
    return structure.wall(col, (0, 0, 0), (WALL_THICKNESS_M, kit["bay"]["backWallHeightM"], depth))


def _right_wall(col: bpy.types.Collection, kit: dict, depth: float) -> list:
    width, height = kit["edges"]["sideWidthM"], kit["edges"]["sideWallHeightM"]
    inner = structure.wall(col, (width - WALL_THICKNESS_M, 0, 0), (width, height, depth))
    if kit["style"] == "symmetric":
        return inner
    return inner + structure.outer_skin_x(col, width, height, depth)


def _back_wall(col: bpy.types.Collection, kit: dict, side: str) -> list:
    width, bay = kit["edges"]["sideWidthM"], kit["bay"]
    objects = structure.wall(col, (0, 0, 0), (width, bay["backWallHeightM"], bay["wallThicknessM"]))
    if side == "right" and kit["style"] != "symmetric":
        # 後牆右端在高於矮牆的部分是剖面，用灰色表示
        objects += structure.outer_skin_x(col, width, bay["backWallHeightM"], bay["wallThicknessM"])
    return objects


def build_side(col: bpy.types.Collection, kit: dict, side: str, variant: str) -> list:
    """side 為 left／right；variant 為 back（第 0 排，含後牆）、base 或 alt（輪替擺設）。"""
    width, depth = kit["edges"]["sideWidthM"], kit["bay"]["rowPitchM"]
    face_z = kit["bay"]["wallThicknessM"]
    objects = structure.floor_slab(col, (width, depth), kit["edges"]["slabDepthM"])
    objects += _left_wall(col, kit, depth) if side == "left" else _right_wall(col, kit, depth)
    if variant == "back":
        objects += _back_wall(col, kit, side)
    if side == "right":
        # 最右欄床位的右側隔簾放在本模組左緣
        top = 2.35 if variant == "back" else 1.8
        objects += privacy_curtain(col, 0.04, (face_z + 0.05, face_z + curtain_depth(kit)), top)
    if kit["style"] == "symmetric":
        return objects + _symmetric_props(col, kit, side, variant)
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


def _symmetric_props(col: bpy.types.Collection, kit: dict, side: str, variant: str) -> list:
    """正視角走道較窄（sideWidthM），道具貼牆排列，前後留出通道。"""
    width, depth = kit["edges"]["sideWidthM"], kit["bay"]["rowPitchM"]
    inner = width - WALL_THICKNESS_M
    if side == "left":
        if variant == "alt":
            return medication_cart(col, WALL_THICKNESS_M + 0.05, depth - 1.0)
        return sanitizer_stand(col, 0.5, depth * 0.62) + linen_cart(col, WALL_THICKNESS_M + 0.05, 0.4)
    if variant == "alt":
        return linen_cart(col, inner - 0.6, 0.5) + wheelchair(col, inner - 0.4, depth - 0.9, -20)
    return sink_counter(col, (inner - SINK_DEPTH_M, inner), (depth * 0.4, depth * 0.4 + 0.8))
