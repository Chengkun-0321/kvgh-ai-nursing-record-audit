"""週期性燈光：每個床位上方一盞暖色面光，任何位置的模組看到的光照都相同。"""

import math

import bpy

from . import scene
from .geometry import to_blender
from .palette import scene_color

LAMP_HEIGHT_M = 2.9
LAMP_SIZE_M = (1.2, 0.6)
LAMP_POWER_W = 55.0
WORLD_STRENGTH = 0.3


def add_ceiling_lamp(col: bpy.types.Collection, x: float, z: float) -> bpy.types.Object:
    """在 (x, z) 上方放一盞朝下的面光。"""
    data = bpy.data.lights.new("ceiling_lamp", "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = LAMP_SIZE_M
    data.energy = LAMP_POWER_W
    data.color = scene_color("lamp")[:3]
    lamp = bpy.data.objects.new("ceiling_lamp", data)
    col.objects.link(lamp)
    lamp.location = to_blender(x, LAMP_HEIGHT_M, z)
    return lamp


def add_lamp_grid(col: bpy.types.Collection, x_range: tuple, z_range: tuple, pitch: tuple) -> list:
    """在範圍內以固定間距排燈；間距與模組格線相同，確保週期一致。"""
    count_x = max(1, math.floor((x_range[1] - x_range[0]) / pitch[0] + 1e-6))
    count_z = max(1, math.floor((z_range[1] - z_range[0]) / pitch[1] + 1e-6))
    return [
        add_ceiling_lamp(col, x_range[0] + (i + 0.5) * pitch[0], z_range[0] + (j + 0.45) * pitch[1])
        for i in range(count_x)
        for j in range(count_z)
    ]


def add_ward_lights(col: bpy.types.Collection, kit: dict, grid: tuple[int, int]) -> None:
    """床位與左右走道各自以模組間距排燈（週期一致），加上均勻環境光。grid 為 (欄, 排)。"""
    bay, side = kit["bay"], kit["edges"]["sideWidthM"]
    width, depth = grid[0] * bay["widthM"], grid[1] * bay["rowPitchM"]
    add_lamp_grid(col, (0, width), (0, depth), (bay["widthM"], bay["rowPitchM"]))
    add_lamp_grid(col, (-side, 0), (0, depth), (side, bay["rowPitchM"]))
    add_lamp_grid(col, (width, width + side), (0, depth), (side, bay["rowPitchM"]))
    scene.set_world_color(bpy.context.scene, scene_color("ambient-glow"), WORLD_STRENGTH)
