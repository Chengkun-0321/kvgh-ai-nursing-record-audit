"""點滴架：五腳底座、立桿、掛勾與點滴袋。"""

import bpy

from ..geometry import CylinderSpec, box, cylinder, rotate_about_y
from . import part

POLE_HEIGHT_M = 1.85
LEG_LENGTH_M = 0.26
LEG_COUNT = 5


def iv_pole(col: bpy.types.Collection, x: float, z: float) -> list:
    """(x, z) 為立桿中心。"""
    objects = [
        cylinder("iv_pole", CylinderSpec((x, 0.05, z), 0.012, POLE_HEIGHT_M), part(col, "metal")),
        cylinder("iv_hub", CylinderSpec((x, 0.04, z), 0.03, 0.05), part(col, "metalDark")),
        box("iv_hook", (x - 0.14, POLE_HEIGHT_M, z - 0.008), (x + 0.14, POLE_HEIGHT_M + 0.015, z + 0.008), part(col, "metal")),
        box("iv_bag", (x + 0.05, POLE_HEIGHT_M - 0.3, z - 0.02), (x + 0.15, POLE_HEIGHT_M - 0.04, z + 0.02), part(col, "window", 0.015)),
        cylinder("iv_line", CylinderSpec((x + 0.1, 0.9, z), 0.003, POLE_HEIGHT_M - 1.2), part(col, "window")),
    ]
    for index in range(LEG_COUNT):
        leg = box(f"iv_leg_{index}", (x, 0.03, z - 0.012), (x + LEG_LENGTH_M, 0.055, z + 0.012), part(col, "metal"))
        caster = cylinder(f"iv_caster_{index}", CylinderSpec((x + LEG_LENGTH_M - 0.02, 0, z), 0.022, 0.03), part(col, "metalDark"))
        rotate_about_y([leg, caster], (x, 0, z), index * 360 / LEG_COUNT + 18)
        objects += [leg, caster]
    return objects

