"""前緣模組：娃娃屋剖面的開口側。

斜視角：只有樓板與左右牆的剖面端。
正視角：地板條加一道低矮的剖面牆（朝相機的外側貼灰色），框出病房前緣又不遮住最前排；
病房外改由前端的地坪延伸填補，不做樓板剖面。
"""

import bpy

from ..props import structure
from .sides import WALL_THICKNESS_M

FRONT_WALL_HEIGHT_M = 0.45


def build_front(col: bpy.types.Collection, kit: dict, variant: str) -> list:
    """variant 為 left／right（寬同側走道）或 fill（寬同床位，每欄一段）。"""
    width = kit["bay"]["widthM"] if variant == "fill" else kit["edges"]["sideWidthM"]
    depth = kit["edges"]["frontDepthM"]
    objects = structure.floor_slab(col, (width, depth), kit["edges"]["slabDepthM"])
    if kit["style"] == "symmetric":
        return objects + _front_wall(col, kit, width, variant)
    if variant == "left":
        height = kit["bay"]["backWallHeightM"]
        objects += structure.wall(col, (0, 0, 0), (WALL_THICKNESS_M, height, depth))
        objects += structure.end_cap_z(col, (0, WALL_THICKNESS_M), height, depth)
    if variant == "right":
        height = kit["edges"]["sideWallHeightM"]
        objects += structure.wall(col, (width - WALL_THICKNESS_M, 0, 0), (width, height, depth))
        objects += structure.outer_skin_x(col, width, height, depth)
        objects += structure.end_cap_z(col, (width - WALL_THICKNESS_M, width + structure.OUTER_SKIN_M), height, depth)
    return objects


def _front_wall(col: bpy.types.Collection, kit: dict, width: float, variant: str) -> list:
    """正視角前緣矮牆；左右端另接側牆延伸到前緣，並以灰色端面收邊。"""
    depth, side_height = kit["edges"]["frontDepthM"], kit["edges"]["sideWallHeightM"]
    face_z = depth - WALL_THICKNESS_M
    objects = structure.wall(col, (0, 0, face_z), (width, FRONT_WALL_HEIGHT_M, depth))
    objects += structure.outer_skin_z(col, (0, width), FRONT_WALL_HEIGHT_M, depth)
    side_x = {"left": (0, WALL_THICKNESS_M), "right": (width - WALL_THICKNESS_M, width)}.get(variant)
    if side_x:
        objects += structure.wall(col, (side_x[0], 0, 0), (side_x[1], side_height, depth))
        objects += structure.end_cap_z(col, side_x, side_height, depth)
    return objects
