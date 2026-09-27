"""材質庫：顏色取自場景 token（globals.css），地板另加程序化地磚紋理。"""

from dataclasses import dataclass

import bpy

from .palette import scene_color

FLOOR_TILE_M = 0.6
FLOOR_GROUT_M = 0.004


@dataclass(frozen=True)
class MaterialSpec:
    """材質參數；emission_strength > 0 表示自發光（燈、螢幕）。"""

    token: str
    roughness: float = 0.8
    metallic: float = 0.0
    emission_strength: float = 0.0


MATERIAL_SPECS: dict[str, MaterialSpec] = {
    "floor": MaterialSpec("floor", 0.34),
    "wall": MaterialSpec("wall", 0.9),
    "wallCap": MaterialSpec("wall-cap", 0.9),
    "wallShade": MaterialSpec("wall-shade", 0.8),
    "wallOuter": MaterialSpec("wall-outer", 0.9),
    "panel": MaterialSpec("panel", 0.5),
    "panelShade": MaterialSpec("panel-shade", 0.6),
    "wood": MaterialSpec("wood", 0.5),
    "woodTop": MaterialSpec("wood-top", 0.45),
    "woodDark": MaterialSpec("wood-shade", 0.55),
    "metal": MaterialSpec("metal", 0.3, 0.8),
    "metalDark": MaterialSpec("metal-dark", 0.45, 0.4),
    "screen": MaterialSpec("screen", 0.25),
    "screenLine": MaterialSpec("screen-line", 0.5, 0.0, 4.0),
    "screenLineAlt": MaterialSpec("screen-line-alt", 0.5, 0.0, 4.0),
    "curtain": MaterialSpec("curtain", 0.95),
    "curtainFold": MaterialSpec("curtain-fold", 0.95),
    "fabric": MaterialSpec("fabric", 0.85),
    "lamp": MaterialSpec("lamp", 0.5, 0.0, 10.0),
    "window": MaterialSpec("window", 0.15, 0.0, 1.2),
    "windowShade": MaterialSpec("window-shade", 0.7),
}


def _principled(mat: bpy.types.Material) -> bpy.types.Node:
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _apply_spec(mat: bpy.types.Material, spec: MaterialSpec) -> None:
    bsdf = _principled(mat)
    color = scene_color(spec.token)
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = spec.roughness
    bsdf.inputs["Metallic"].default_value = spec.metallic
    if spec.emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value = color
        bsdf.inputs["Emission Strength"].default_value = spec.emission_strength
    mat.diffuse_color = color


def _add_floor_tiles(mat: bpy.types.Material) -> None:
    """0.6 m 地磚；以物件座標取樣，模組原點都在 0.6 的倍數上，拼接後磚縫連續。"""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    coords, brick = nodes.new("ShaderNodeTexCoord"), nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    base = scene_color("floor")
    brick.inputs["Color1"].default_value = base
    brick.inputs["Color2"].default_value = tuple(c * 0.96 for c in base[:3]) + (1.0,)
    brick.inputs["Mortar"].default_value = tuple(c * 0.82 for c in base[:3]) + (1.0,)
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = FLOOR_GROUT_M
    brick.inputs["Brick Width"].default_value = FLOOR_TILE_M
    brick.inputs["Row Height"].default_value = FLOOR_TILE_M
    links.new(coords.outputs["Object"], brick.inputs["Vector"])
    links.new(brick.outputs["Color"], _principled(mat).inputs["Base Color"])


def material(key: str) -> bpy.types.Material:
    """取得（或建立）指定材質；同名材質整個場景共用。"""
    name = f"ward_{key}"
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    _apply_spec(mat, MATERIAL_SPECS[key])
    if key == "floor":
        _add_floor_tiles(mat)
    return mat
