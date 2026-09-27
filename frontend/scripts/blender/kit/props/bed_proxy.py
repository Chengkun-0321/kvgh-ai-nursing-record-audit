"""病床代理物：相機看不到，只負責投射陰影，讓去背圖病床「落地」。

尺寸取自去背圖校準（腳輪間距約 0.84 × 1.9 m，床尾板高約 0.65 m）。
"""

import bpy

from ..geometry import box
from . import part

HALF_WIDTH_M = 0.47
HALF_LENGTH_M = 1.05


def bed_proxy(col: bpy.types.Collection, x: float, z: float) -> list:
    """(x, z) 為床心；床頭朝 -Z。"""
    objects = [
        box("bed_proxy_base", (x - 0.42, 0.12, z - 0.95), (x + 0.42, 0.3, z + 0.95), part(col, "metalDark")),
        box("bed_proxy_mattress", (x - HALF_WIDTH_M, 0.3, z - HALF_LENGTH_M + 0.05), (x + HALF_WIDTH_M, 0.55, z + HALF_LENGTH_M - 0.05), part(col, "wall")),
        box("bed_proxy_head", (x - HALF_WIDTH_M, 0.3, z - HALF_LENGTH_M), (x + HALF_WIDTH_M, 0.8, z - HALF_LENGTH_M + 0.06), part(col, "wall")),
        box("bed_proxy_foot", (x - HALF_WIDTH_M, 0.3, z + HALF_LENGTH_M - 0.06), (x + HALF_WIDTH_M, 0.65, z + HALF_LENGTH_M), part(col, "wall")),
    ]
    for obj in objects:
        obj.visible_camera = False
    return objects
