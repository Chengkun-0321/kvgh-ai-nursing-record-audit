"""預覽用：把病床去背圖放成正對相機的平面，位置公式與前端 wardProjection.ts 相同。"""

import math
from pathlib import Path

import bpy
import numpy as np

from . import view
from .geometry import to_blender

# 平面再往相機拉 2 cm，避免與地板深度相同而閃爍
DEPTH_EPSILON_M = 0.02


def sprite_plane_center(anchor: tuple, kit: dict) -> np.ndarray:
    """回傳平面中心（前端座標）；平面沿視線前移 d，確保圖片最下緣不低於地板。"""
    sprite, pitch = kit["sprite"], math.radians(kit["view"]["pitchDeg"])
    right, up, forward = view.view_basis(kit["view"]["yawDeg"], kit["view"]["pitchDeg"])
    plane_w = sprite["planeWidthM"]
    plane_h = plane_w * sprite["heightPx"] / sprite["widthPx"]
    ax, ay = sprite["anchorPx"]["x"], sprite["anchorPx"]["y"]
    below_anchor_m = plane_h * (sprite["contentRectPx"]["bottom"] - ay) / sprite["heightPx"]
    lift = below_anchor_m / math.tan(pitch) + DEPTH_EPSILON_M
    center = np.array([anchor[0], 0.0, anchor[1]]) - forward * lift
    center -= right * (ax / sprite["widthPx"] - 0.5) * plane_w
    return center - up * (0.5 - ay / sprite["heightPx"]) * plane_h


def _sprite_material(image_path: Path) -> bpy.types.Material:
    mat = bpy.data.materials.new(f"sprite_{image_path.stem}")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(image_path), check_existing=True)
    emission, transparent = nodes.new("ShaderNodeEmission"), nodes.new("ShaderNodeBsdfTransparent")
    mix, output = nodes.new("ShaderNodeMixShader"), nodes.new("ShaderNodeOutputMaterial")
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(texture.outputs["Alpha"], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    return mat


def add_sprite(col: bpy.types.Collection, image_path: Path, anchor: tuple, kit: dict) -> bpy.types.Object:
    """在床心 anchor（前端 x、z）放一片去背圖平面。"""
    sprite = kit["sprite"]
    plane_w = sprite["planeWidthM"]
    plane_h = plane_w * sprite["heightPx"] / sprite["widthPx"]
    mesh = bpy.data.meshes.new("bed_sprite")
    half_w, half_h = plane_w / 2, plane_h / 2
    mesh.from_pydata([(-half_w, -half_h, 0), (half_w, -half_h, 0), (half_w, half_h, 0), (-half_w, half_h, 0)], [], [(0, 1, 2, 3)])
    mesh.uv_layers.new().data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    mesh.materials.append(_sprite_material(image_path))
    obj = bpy.data.objects.new("bed_sprite", mesh)
    col.objects.link(obj)
    obj.location = to_blender(*sprite_plane_center(anchor, kit))
    obj.rotation_euler = view.blender_camera_rotation(kit["view"])
    return obj
