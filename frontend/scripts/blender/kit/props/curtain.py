"""床間隔簾：收攏在床頭牆邊的布簾與天花軌道。"""

import math

import bmesh
import bpy

from ..geometry import box, to_blender
from ..materials import material
from . import part

FOLD_COUNT = 9
FOLD_AMPLITUDE_M = 0.05
SAMPLES_PER_FOLD = 6
HEM_Y_M = 0.12


def _curtain_sheet(col: bpy.types.Collection, x: float, z_range: tuple, top_y: float) -> bpy.types.Object:
    """以正弦波折出布簾皺褶；雙面可見所以加 solidify 修飾器。"""
    samples = FOLD_COUNT * SAMPLES_PER_FOLD + 1
    bm = bmesh.new()
    columns = []
    for index in range(samples):
        t = index / (samples - 1)
        z = z_range[0] + (z_range[1] - z_range[0]) * t
        dx = FOLD_AMPLITUDE_M * math.sin(t * FOLD_COUNT * 2 * math.pi)
        columns.append([bm.verts.new(to_blender(x + dx, y, z)) for y in (HEM_Y_M, top_y)])
    for left, right in zip(columns[:-1], columns[1:]):
        bm.faces.new((left[0], right[0], right[1], left[1]))
    mesh = bpy.data.meshes.new("curtain")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material("curtain"))
    obj = bpy.data.objects.new("curtain", mesh)
    col.objects.link(obj)
    obj.modifiers.new("Solidify", "SOLIDIFY").thickness = 0.008
    return obj


def privacy_curtain(col: bpy.types.Collection, x: float, z_range: tuple, top_y: float) -> list:
    """x 為床位邊界；z_range 為布簾前後範圍；top_y 為軌道高度。"""
    track_lo = (x - 0.015, top_y + 0.02, z_range[0] - 0.05)
    track_hi = (x + 0.015, top_y + 0.05, z_range[1] + 0.25)
    track = box("curtain_track", track_lo, track_hi, part(col, "metal"))
    return [_curtain_sheet(col, x, z_range, top_y), track]

