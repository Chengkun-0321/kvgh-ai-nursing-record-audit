"""算圖環境：以 4 欄 × 3 排的病房包住目標模組，讓陰影、反光在模組接縫處連續。"""

from dataclasses import dataclass

import bpy

from . import layout, lighting
from .geometry import offset
from .modules import MODULE_BUILDERS

CONTEXT_COLUMNS, CONTEXT_ROWS = 4, 3


@dataclass
class ContextWard:
    """整個算圖環境：每個模組擺放及其物件。"""

    columns: int
    rows: int
    modules: list[tuple[layout.Placement, list]]


def build_context_ward(kit: dict) -> ContextWard:
    """以實體物件（非 instance）建立環境，才能逐一設定相機可見性。"""
    collection = bpy.data.collections.new("context")
    bpy.context.scene.collection.children.link(collection)
    modules = []
    for placement in layout.module_placements(CONTEXT_COLUMNS, CONTEXT_ROWS, kit):
        objects = MODULE_BUILDERS[placement.module_id](collection, kit)
        offset(objects, placement.x, placement.z)
        modules.append((placement, objects))
    lighting.add_ward_lights(collection, kit, (CONTEXT_COLUMNS, CONTEXT_ROWS))
    return ContextWard(CONTEXT_COLUMNS, CONTEXT_ROWS, modules)


def pick_target(ward: ContextWard, module_id: str, kit: dict) -> tuple[layout.Placement, list]:
    """同一模組有多個擺放時，取最靠近病房中央者（四周都有鄰居，光照最具代表性）。"""
    width, pitch = kit["bay"]["widthM"], kit["bay"]["rowPitchM"]
    center_x, center_z = ward.columns * width / 2, ward.rows * pitch / 2
    candidates = [entry for entry in ward.modules if entry[0].module_id == module_id]
    return min(candidates, key=lambda e: (e[0].x + width / 2 - center_x) ** 2 + (e[0].z + pitch / 2 - center_z) ** 2)


def all_objects(ward: ContextWard) -> list:
    """環境中所有模組物件。"""
    return [obj for _, objects in ward.modules for obj in objects]
