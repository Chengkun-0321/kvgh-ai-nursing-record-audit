"""模組合併、剔除背面、指定投影貼圖材質並匯出 GLB。"""

from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

from . import view
from .geometry import to_blender

WEBP_QUALITY = 88


def join_evaluated(objects: list, name: str) -> bpy.types.Object:
    """套用修飾器與世界變換後合併成單一網格（一個模組 = 一次 draw call）。"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.transform(evaluated.matrix_world)
        bm.from_mesh(mesh)
        evaluated.to_mesh_clear()
    joined = bpy.data.meshes.new(name)
    bm.to_mesh(joined)
    bm.free()
    obj = bpy.data.objects.new(name, joined)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def cull_back_faces(obj: bpy.types.Object, kit: dict) -> None:
    """相機永不旋轉，背對相機的面永遠看不到，直接刪除以縮小檔案。"""
    _, _, forward = view.view_basis(kit["view"]["yawDeg"], kit["view"]["pitchDeg"])
    toward_camera = -to_blender(*forward)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    hidden = [face for face in bm.faces if face.normal.dot(toward_camera) <= 1e-4]
    bmesh.ops.delete(bm, geom=hidden, context="FACES")
    loose = [vert for vert in bm.verts if not vert.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()


def move_origin(obj: bpy.types.Object, x: float, z: float) -> None:
    """把模組頂點平移到以 (x, z)（前端座標）為原點，對應前端擺放時的模組原點。"""
    obj.data.transform(Matrix.Translation(-to_blender(x, 0, z)))


def assign_texture(obj: bpy.types.Object, image_path: Path, use_alpha: bool) -> None:
    """單一材質、單一貼圖；前端以無光照材質顯示，這裡只需 baseColor。"""
    mat = bpy.data.materials.new(obj.name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(image_path), check_existing=False)
    texture.image.pack()
    texture.interpolation = "Linear"
    links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    if use_alpha:
        links.new(texture.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 1.0
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def export_glb(obj: bpy.types.Object, path: Path) -> None:
    """只匯出該物件；貼圖轉 WebP，不匯出法線（無光照材質用不到）。"""
    for other in bpy.context.scene.objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_image_format="WEBP",
        export_image_quality=WEBP_QUALITY,
        export_normals=False,
        export_materials="EXPORT",
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )
