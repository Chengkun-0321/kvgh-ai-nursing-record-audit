"""走道設施：洗手台、乾洗手架。"""

import bpy

from ..geometry import CylinderSpec, box, cylinder
from . import part

COUNTER_Y = 0.85


def sink_counter(col: bpy.types.Collection, x_range: tuple, z_range: tuple) -> list:
    """靠右側矮牆的洗手台；x_range 右端貼牆。"""
    (x0, x1), (z0, z1) = x_range, z_range
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    return [
        box("sink_cabinet", (x0, 0.08, z0), (x1, COUNTER_Y - 0.04, z1), part(col, "wood", 0.01)),
        box("sink_top", (x0 - 0.02, COUNTER_Y - 0.04, z0 - 0.02), (x1, COUNTER_Y, z1 + 0.02), part(col, "wallCap", 0.008)),
        box("sink_basin", (cx - 0.16, COUNTER_Y - 0.035, cz - 0.2), (cx + 0.12, COUNTER_Y + 0.002, cz + 0.2), part(col, "metal")),
        cylinder("sink_faucet", CylinderSpec((x1 - 0.06, COUNTER_Y, cz), 0.015, 0.22), part(col, "metal")),
        box("sink_spout", (cx + 0.02, COUNTER_Y + 0.19, cz - 0.012), (x1 - 0.06, COUNTER_Y + 0.215, cz + 0.012), part(col, "metal")),
    ]


def sanitizer_stand(col: bpy.types.Collection, x: float, z: float) -> list:
    """立式乾洗手架。"""
    return [
        cylinder("sanitizer_base", CylinderSpec((x, 0, z), 0.14, 0.03), part(col, "metalDark")),
        cylinder("sanitizer_pole", CylinderSpec((x, 0.03, z), 0.015, 1.0), part(col, "metal")),
        box("sanitizer_bottle", (x - 0.06, 1.0, z - 0.05), (x + 0.06, 1.24, z + 0.05), part(col, "wall", 0.01)),
        box("sanitizer_label", (x - 0.04, 1.08, z + 0.05), (x + 0.04, 1.16, z + 0.052), part(col, "screenLine")),
    ]
