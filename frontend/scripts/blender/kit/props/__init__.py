"""場景道具：每個函式在指定位置（前端座標，公尺）建立一組物件並回傳。"""

import bpy

from ..geometry import Part
from ..materials import material


def part(collection: bpy.types.Collection, key: str, bevel_m: float = 0.0) -> Part:
    """用材質 key 組出 Part，讓道具程式碼保持簡短。"""
    return Part(collection, material(key), bevel_m)
