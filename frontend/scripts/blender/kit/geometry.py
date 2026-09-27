"""建模工具：所有尺寸以前端座標（X 右、Y 上、+Z 朝前）傳入，內部換成 Blender 座標。"""

import math
from dataclasses import dataclass

import bmesh
import bpy
from mathutils import Matrix, Vector


def to_blender(x: float, y: float, z: float) -> Vector:
    """前端座標 → Blender 座標（Z 向上、+Y 朝後）。"""
    return Vector((x, -z, y))


@dataclass(frozen=True)
class Part:
    """建模時的共用參數：放進哪個 collection、用哪個材質、圓角寬度（0 表示直角）。"""

    collection: bpy.types.Collection
    material: bpy.types.Material
    bevel_m: float = 0.0


@dataclass(frozen=True)
class CylinderSpec:
    """圓柱參數：base 為底面圓心（前端座標），axis 為延伸方向 x／y／z。"""

    base: tuple
    radius: float
    height: float
    axis: str = "y"


def _link_mesh(name: str, bm: bmesh.types.BMesh, part: Part) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(part.material)
    obj = bpy.data.objects.new(name, mesh)
    part.collection.objects.link(obj)
    return obj


def box(name: str, lo: tuple, hi: tuple, part: Part) -> bpy.types.Object:
    """以兩個對角點（前端座標）建立長方體；part.bevel_m > 0 時加圓角修飾器。"""
    size = Vector(hi) - Vector(lo)
    center = (Vector(lo) + Vector(hi)) / 2
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((size.x, size.z, size.y)), verts=bm.verts)
    bmesh.ops.translate(bm, vec=to_blender(*center), verts=bm.verts)
    obj = _link_mesh(name, bm, part)
    if part.bevel_m > 0:
        add_bevel(obj, part.bevel_m)
    return obj


# 把沿 Blender Z 建立的圓柱轉到指定軸向；前端 +Z 對應 Blender -Y
AXIS_ROTATIONS = {
    "y": Matrix.Identity(3),
    "x": Matrix.Rotation(math.pi / 2, 3, "Y"),
    "z": Matrix.Rotation(math.pi / 2, 3, "X"),
}


def cylinder(name: str, spec: CylinderSpec, part: Part) -> bpy.types.Object:
    """建立圓柱（16 段；小道具在此視距下已足夠圓滑）。"""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=spec.radius, radius2=spec.radius, depth=spec.height)
    bmesh.ops.translate(bm, vec=Vector((0, 0, spec.height / 2)), verts=bm.verts)
    bmesh.ops.rotate(bm, cent=Vector(), matrix=AXIS_ROTATIONS[spec.axis], verts=bm.verts)
    bmesh.ops.translate(bm, vec=to_blender(*spec.base), verts=bm.verts)
    return _link_mesh(name, bm, part)


def add_bevel(obj: bpy.types.Object, width_m: float, segments: int = 2) -> None:
    """圓角讓烘焙後的邊緣有高光與陰影，比直角方塊寫實。"""
    modifier = obj.modifiers.new("Bevel", "BEVEL")
    modifier.width = width_m
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def rotate_about_y(objects: list, pivot: tuple, degrees: float) -> None:
    """繞前端 Y 軸（Blender Z 軸）旋轉一組物件，用於椅子等需要轉向的道具。"""
    rotation = Matrix.Translation(to_blender(*pivot)) @ Matrix.Rotation(math.radians(degrees), 4, "Z") @ Matrix.Translation(-to_blender(*pivot))
    for obj in objects:
        obj.matrix_world = rotation @ obj.matrix_world


def offset(objects: list, dx: float, dz: float) -> None:
    """在地面上平移一組物件（前端座標的 x、z）。"""
    delta = to_blender(dx, 0, dz)
    for obj in objects:
        obj.location += delta
