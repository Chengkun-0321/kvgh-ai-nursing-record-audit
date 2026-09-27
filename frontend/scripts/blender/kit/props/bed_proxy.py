"""病床代理物：相機看不到，只負責投射陰影，讓去背圖病床「落地」。

尺寸取自設定檔 bedProxy（依各視角去背圖的床體比例校準；斜視角約 0.94 × 2.1 m，
正視角的生成圖床身較短，約 0.96 × 1.1 m）。
"""

import bpy

from ..geometry import box
from . import part

BASE_TOP_M = 0.3
MATTRESS_TOP_M = 0.55
# 床架底座比床面內縮，陰影邊緣才有層次
BASE_INSET_M = (0.05, 0.1)
BOARD_DEPTH_M = 0.06


def bed_proxy(col: bpy.types.Collection, anchor: tuple, dims: dict) -> list:
    """anchor 為床心 (x, z)；床頭朝 -Z。"""
    x, z = anchor
    hw, hl = dims["halfWidthM"], dims["halfLengthM"]
    bw, bl = hw - BASE_INSET_M[0], hl - BASE_INSET_M[1]
    objects = [
        box("bed_proxy_base", (x - bw, 0.12, z - bl), (x + bw, BASE_TOP_M, z + bl), part(col, "metalDark")),
        box("bed_proxy_mattress", (x - hw, BASE_TOP_M, z - hl + 0.05), (x + hw, MATTRESS_TOP_M, z + hl - 0.05), part(col, "wall")),
        box("bed_proxy_head", (x - hw, BASE_TOP_M, z - hl), (x + hw, dims["headHeightM"], z - hl + BOARD_DEPTH_M), part(col, "wall")),
        box("bed_proxy_foot", (x - hw, BASE_TOP_M, z + hl - BOARD_DEPTH_M), (x + hw, dims["footHeightM"], z + hl), part(col, "wall")),
    ]
    for obj in objects:
        obj.visible_camera = False
    return objects
