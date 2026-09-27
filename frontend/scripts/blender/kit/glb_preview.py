"""以匯出的 GLB 組裝病房：材質改成無光照（自發光），與前端 MeshBasicMaterial 的呈現相同。"""

from pathlib import Path

import bpy

from . import config
from .geometry import to_blender


def _make_unlit(mat: bpy.types.Material, use_alpha: bool) -> None:
    """把 Principled 換成 Emission（強度 1 = 貼圖原色），必要時保留 alpha。"""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    texture = next(n for n in nodes if n.type == "TEX_IMAGE")
    output = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    emission = nodes.new("ShaderNodeEmission")
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    if not use_alpha:
        links.new(emission.outputs[0], output.inputs["Surface"])
        return
    transparent, mix = nodes.new("ShaderNodeBsdfTransparent"), nodes.new("ShaderNodeMixShader")
    links.new(texture.outputs["Alpha"], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"


def import_source(path: Path, use_alpha: bool) -> bpy.types.Collection:
    """匯入 GLB 到獨立 collection（不連到場景，供 instance 使用）。"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    source = bpy.data.collections.new(f"glb_{path.stem}")
    for obj in imported:
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        source.objects.link(obj)
        for slot in obj.material_slots:
            _make_unlit(slot.material, use_alpha)
    return source


def instance(target: bpy.types.Collection, source: bpy.types.Collection, x: float, z: float) -> None:
    """在 (x, z) 放一個 collection instance。"""
    empty = bpy.data.objects.new(source.name, None)
    empty.instance_type = "COLLECTION"
    empty.instance_collection = source
    empty.location = to_blender(x, 0, z)
    target.objects.link(empty)


def place_glb_modules(target: bpy.types.Collection, placements: list, kit: dict) -> None:
    """每種模組匯入一次，依擺放清單建立 instance。"""
    sources = {}
    for placement in placements:
        if placement.module_id not in sources:
            path = config.MODEL_OUT_DIR / kit["modules"][placement.module_id]["file"]
            sources[placement.module_id] = import_source(path, use_alpha=False)
        instance(target, sources[placement.module_id], placement.x, placement.z)


def place_bed_shadows(target: bpy.types.Collection, anchors: list, kit: dict) -> None:
    """每床一片床下陰影貼花。"""
    source = import_source(config.MODEL_OUT_DIR / kit["decals"]["bedShadow"]["file"], use_alpha=True)
    for x, z in anchors:
        instance(target, source, x, z)
