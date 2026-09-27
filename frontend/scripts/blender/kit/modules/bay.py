"""床位空間模組（bay）：第 0 排靠全高後牆，其餘排靠床頭隔屏。

模組原點在地板左後角；床本身是前端的去背圖，這裡只建周邊設施。
道具左右配置依相機 yaw 決定：相機略朝左看，高物件的投影往左後方延伸，
所以監視器、床頭櫃放左側，點滴架、陪病椅放右側，才不會遮到後排病床。
"""

import bpy

from ..props import structure
from ..props.curtain import privacy_curtain
from ..props.furniture import bedside_cabinet, visitor_chair
from ..props.headwall import headwall_rail, wood_accent
from ..props.iv_pole import iv_pole
from ..props.monitor import wall_monitor
from ..props.window import light_strip

CURTAIN_TOP_M = 2.35
SPINE_CURTAIN_TOP_M = 1.8
CURTAIN_DEPTH_M = 1.4
ACCENT_HALF_WIDTH_M = 0.62


def _bedside(col: bpy.types.Collection, bay: dict, face_z: float) -> list:
    """兩種床位共用：床頭櫃、點滴架、陪病椅、左緣隔簾。"""
    width, center_z = bay["widthM"], bay["bedCenterM"]
    return [
        *bedside_cabinet(col, 0.12, face_z + 0.15),
        *iv_pole(col, width - 0.38, face_z + 0.35),
        *visitor_chair(col, width - 0.36, center_z + 0.5, -70),
        *structure.baseboard(col, (0, 0, face_z), (width, 0.1, face_z + 0.015)),
    ]


def _curtain(col: bpy.types.Collection, face_z: float, top_y: float) -> list:
    return privacy_curtain(col, 0.04, (face_z + 0.05, face_z + CURTAIN_DEPTH_M), top_y)


def build_backwall_bay(col: bpy.types.Collection, kit: dict) -> list:
    """第 0 排床位：全高後牆、深色木飾板、牆頂燈帶。"""
    bay = kit["bay"]
    width, depth, face_z, height = bay["widthM"], bay["rowPitchM"], bay["wallThicknessM"], bay["backWallHeightM"]
    mid = width / 2
    return [
        *structure.floor_slab(col, width, depth),
        *structure.wall(col, (0, 0, 0), (width, height, face_z)),
        *wood_accent(col, (mid - ACCENT_HALF_WIDTH_M, mid + ACCENT_HALF_WIDTH_M), (0.7, 2.15), face_z),
        *headwall_rail(col, (0.28, width - 0.28), 1.3, face_z + 0.025),
        *light_strip(col, (0.0, width), height - 0.12, face_z),
        *wall_monitor(col, 0.36, 1.62, face_z),
        *_curtain(col, face_z, CURTAIN_TOP_M),
        *_bedside(col, bay, face_z),
    ]


def build_spine_bay(col: bpy.types.Collection, kit: dict) -> list:
    """第 1 排之後：矮隔屏當床頭牆，隔簾較低以免遮住後排。"""
    bay = kit["bay"]
    width, depth, face_z, height = bay["widthM"], bay["rowPitchM"], bay["wallThicknessM"], bay["spineHeightM"]
    mid = width / 2
    return [
        *structure.floor_slab(col, width, depth),
        *structure.wall(col, (0, 0, 0), (width, height, face_z)),
        *wood_accent(col, (mid - ACCENT_HALF_WIDTH_M, mid + ACCENT_HALF_WIDTH_M), (0.35, height - 0.05), face_z),
        *headwall_rail(col, (0.28, width - 0.28), height - 0.32, face_z + 0.025),
        *wall_monitor(col, 0.36, height - 0.18, face_z),
        *_curtain(col, face_z, SPINE_CURTAIN_TOP_M),
        *_bedside(col, bay, face_z),
    ]
