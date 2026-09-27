"""壁掛生理監視器：支臂、機身、彩色波形螢幕。"""

import bpy

from ..geometry import CylinderSpec, box, cylinder
from . import part

SCREEN_W, SCREEN_H, BODY_D = 0.46, 0.36, 0.08
ARM_LENGTH_M = 0.25
# 波形：(離螢幕底部高度, 寬度比例, 材質)
TRACES = ((0.07, 0.7, "screenLine"), (0.13, 0.55, "screenLineAlt"), (0.19, 0.7, "screenLine"), (0.25, 0.4, "window"))


def wall_monitor(col: bpy.types.Collection, x: float, bottom_y: float, face_z: float) -> list:
    """支臂自牆面伸出，螢幕略向前。"""
    front_z = face_z + ARM_LENGTH_M
    half = SCREEN_W / 2
    screen_z = front_z + BODY_D
    objects = [
        cylinder("monitor_arm", CylinderSpec((x, bottom_y + 0.1, face_z), 0.02, ARM_LENGTH_M, "z"), part(col, "metal")),
        box("monitor_body", (x - half, bottom_y, front_z), (x + half, bottom_y + SCREEN_H, screen_z), part(col, "metalDark", 0.012)),
        box("monitor_screen", (x - half + 0.02, bottom_y + 0.03, screen_z), (x + half - 0.02, bottom_y + SCREEN_H - 0.03, screen_z + 0.004), part(col, "screen")),
    ]
    for index, (y, ratio, key) in enumerate(TRACES):
        lo = (x - half + 0.04, bottom_y + y, screen_z + 0.004)
        hi = (x - half + 0.04 + (SCREEN_W - 0.08) * ratio, bottom_y + y + 0.01, screen_z + 0.006)
        objects.append(box(f"monitor_trace_{index}", lo, hi, part(col, key)))
    return objects
