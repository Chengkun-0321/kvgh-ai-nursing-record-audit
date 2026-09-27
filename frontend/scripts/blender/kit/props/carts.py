"""推車類：給藥車、布品車、輪椅。"""

import bpy

from ..geometry import CylinderSpec, box, cylinder, rotate_about_y
from . import part

WHEEL_R = 0.05


def _casters(col: bpy.types.Collection, lo: tuple, hi: tuple) -> list:
    corners = ((lo[0] + 0.05, lo[1] + 0.05), (hi[0] - 0.05, lo[1] + 0.05), (lo[0] + 0.05, hi[1] - 0.05), (hi[0] - 0.05, hi[1] - 0.05))
    return [cylinder("cart_caster", CylinderSpec((x - 0.015, WHEEL_R, z), WHEEL_R, 0.03, "x"), part(col, "metalDark")) for x, z in corners]


def medication_cart(col: bpy.types.Collection, x: float, z: float) -> list:
    """(x, z) 為左後角；多層抽屜，頂部把手。"""
    w, d, h = 0.6, 0.48, 1.0
    objects = [box("cart_body", (x, 0.1, z), (x + w, h, z + d), part(col, "wall", 0.015))]
    for index in range(5):
        y = 0.18 + index * 0.16
        objects.append(box("cart_drawer", (x + 0.03, y, z + d), (x + w - 0.03, y + 0.13, z + d + 0.01), part(col, "curtain", 0.005)))
    objects.append(box("cart_handle", (x - 0.02, h - 0.1, z + d), (x + w + 0.02, h - 0.07, z + d + 0.06), part(col, "metal")))
    return objects + _casters(col, (x, z), (x + w, z + d))


def linen_cart(col: bpy.types.Collection, x: float, z: float) -> list:
    """(x, z) 為左後角；框架加布袋。"""
    w, d = 0.55, 0.7
    return [
        box("linen_frame", (x, 0.1, z), (x + w, 0.14, z + d), part(col, "metal")),
        box("linen_bag", (x + 0.02, 0.14, z + 0.02), (x + w - 0.02, 0.95, z + d - 0.02), part(col, "curtain", 0.04)),
        box("linen_rim", (x, 0.95, z), (x + w, 0.98, z + d), part(col, "metal")),
    ] + _casters(col, (x, z), (x + w, z + d))


def wheelchair(col: bpy.types.Collection, x: float, z: float, facing_deg: float) -> list:
    """(x, z) 為座面中心；簡化為大輪、座墊、椅背與扶手。"""
    objects = [
        box("wc_seat", (x - 0.22, 0.46, z - 0.22), (x + 0.22, 0.52, z + 0.22), part(col, "fabric", 0.02)),
        box("wc_back", (x - 0.22, 0.52, z - 0.24), (x + 0.22, 0.95, z - 0.2), part(col, "fabric", 0.02)),
        box("wc_footrest", (x - 0.18, 0.08, z + 0.3), (x + 0.18, 0.11, z + 0.42), part(col, "metalDark")),
    ]
    for side in (-1, 1):
        objects.append(cylinder("wc_wheel", CylinderSpec((x + side * 0.27 - 0.015, 0.3, z - 0.05), 0.3, 0.03, "x"), part(col, "metalDark")))
        objects.append(box("wc_arm", (x + side * 0.24 - 0.02, 0.52, z - 0.2), (x + side * 0.24 + 0.02, 0.72, z + 0.2), part(col, "metal")))
        objects.append(cylinder("wc_front_caster", CylinderSpec((x + side * 0.18 - 0.01, 0.06, z + 0.3), 0.06, 0.02, "x"), part(col, "metalDark")))
    rotate_about_y(objects, (x, 0, z), facing_deg)
    return objects
