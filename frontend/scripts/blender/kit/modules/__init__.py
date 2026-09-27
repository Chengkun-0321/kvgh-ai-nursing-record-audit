"""模組登錄表：wardKit.json 的模組 id → 建模函式。"""

from collections.abc import Callable

import bpy

from .bay import build_backwall_bay, build_spine_bay
from .front import build_front
from .sides import build_side

ModuleBuilder = Callable[[bpy.types.Collection, dict], list]

MODULE_BUILDERS: dict[str, ModuleBuilder] = {
    "bayBackwall": build_backwall_bay,
    "baySpine": build_spine_bay,
    "sideBackLeft": lambda col, kit: build_side(col, kit, "left", "back"),
    "sideBackRight": lambda col, kit: build_side(col, kit, "right", "back"),
    "sideLeft": lambda col, kit: build_side(col, kit, "left", "base"),
    "sideRight": lambda col, kit: build_side(col, kit, "right", "base"),
    "sideLeftAlt": lambda col, kit: build_side(col, kit, "left", "alt"),
    "sideRightAlt": lambda col, kit: build_side(col, kit, "right", "alt"),
    "frontLeft": lambda col, kit: build_front(col, kit, "left"),
    "frontRight": lambda col, kit: build_front(col, kit, "right"),
    "frontFill": lambda col, kit: build_front(col, kit, "fill"),
}


def build_module(module_id: str, kit: dict) -> bpy.types.Collection:
    """在獨立 collection 中建立模組（不連到場景，供實例化或匯出）。"""
    collection = bpy.data.collections.new(f"module_{module_id}")
    MODULE_BUILDERS[module_id](collection, kit)
    return collection
