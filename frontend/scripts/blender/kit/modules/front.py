"""前緣模組：娃娃屋剖面的開口側，只有樓板與左右牆的剖面端。"""

import bpy

from ..props import structure
from .sides import WALL_THICKNESS_M


def build_front(col: bpy.types.Collection, kit: dict, variant: str) -> list:
    """variant 為 left／right（寬同側走道）或 fill（寬同床位，每欄一段）。"""
    width = kit["bay"]["widthM"] if variant == "fill" else kit["edges"]["sideWidthM"]
    depth = kit["edges"]["frontDepthM"]
    objects = structure.floor_slab(col, width, depth)
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
