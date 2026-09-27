"""固定相機投影貼圖：模組在固定視角下算圖，再把圖片依頂點的螢幕位置貼回模型。

相機只平移、縮放而不旋轉，所以網頁上看到的每個表面，
都與 Blender 算圖時的視角相同，反光與柔和陰影可直接保留。
"""

import math
from dataclasses import dataclass

import bpy
import numpy as np

from . import view
from .geometry import to_blender

MARGIN_PX = 4


@dataclass(frozen=True)
class ScreenFrame:
    """算圖範圍：左下角 (u0, v0) 與寬高（公尺，相機平面座標）及解析度。"""

    u0: float
    v0: float
    width_m: float
    height_m: float
    resolution: tuple[int, int]


def world_vertices(objects: list) -> np.ndarray:
    """取得套用修飾器後的世界座標頂點，換成前端座標。"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points += [evaluated.matrix_world @ v.co for v in mesh.vertices]
        evaluated.to_mesh_clear()
    blender = np.array(points)
    return np.stack([blender[:, 0], blender[:, 2], -blender[:, 1]], axis=1)


def fit_frame(points: np.ndarray, kit: dict, px_per_meter: float) -> ScreenFrame:
    """框住所有頂點並對齊整數像素，保證 UV 與算圖像素一一對應。"""
    right, up, _ = view.view_basis(kit["view"]["yawDeg"], kit["view"]["pitchDeg"])
    u, v = points @ right, points @ up
    margin = MARGIN_PX / px_per_meter
    res_x = math.ceil((u.max() - u.min() + 2 * margin) * px_per_meter)
    res_y = math.ceil((v.max() - v.min() + 2 * margin) * px_per_meter)
    return ScreenFrame(u.min() - margin, v.min() - margin, res_x / px_per_meter, res_y / px_per_meter, (res_x, res_y))


def place_camera(render_scene: bpy.types.Scene, kit: dict, frame: ScreenFrame) -> bpy.types.Object:
    """建立對準 frame 的正交相機。"""
    right, up, forward = view.view_basis(kit["view"]["yawDeg"], kit["view"]["pitchDeg"])
    center = right * (frame.u0 + frame.width_m / 2) + up * (frame.v0 + frame.height_m / 2)
    data = bpy.data.cameras.new("projection_camera")
    data.type, data.sensor_fit = "ORTHO", "AUTO"
    data.ortho_scale = max(frame.width_m, frame.height_m)
    data.clip_start, data.clip_end = 0.1, 300.0
    camera = bpy.data.objects.new("projection_camera", data)
    render_scene.collection.objects.link(camera)
    camera.location = to_blender(*(center - forward * 100.0))
    camera.rotation_euler = view.blender_camera_rotation(kit["view"])
    render_scene.camera = camera
    render_scene.render.resolution_x, render_scene.render.resolution_y = frame.resolution
    render_scene.render.resolution_percentage = 100
    return camera


def assign_projected_uvs(obj: bpy.types.Object, kit: dict, frame: ScreenFrame) -> None:
    """每個頂點的 UV = 它在算圖中的像素位置（0–1）；obj 須已套用世界變換。"""
    right, up, _ = view.view_basis(kit["view"]["yawDeg"], kit["view"]["pitchDeg"])
    mesh = obj.data
    blender = np.array([v.co for v in mesh.vertices])
    points = np.stack([blender[:, 0], blender[:, 2], -blender[:, 1]], axis=1)
    uv_per_vertex = np.stack([(points @ right - frame.u0) / frame.width_m, (points @ up - frame.v0) / frame.height_m], axis=1)
    loop_vertices = np.zeros(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loop_vertices)
    for layer in list(mesh.uv_layers):
        mesh.uv_layers.remove(layer)
    mesh.uv_layers.new(name="projected").data.foreach_set("uv", uv_per_vertex[loop_vertices].reshape(-1))


def set_camera_visibility(visible: list, hidden: list) -> None:
    """hidden 仍投射陰影與出現在反光中，只是不被相機直接看到。"""
    for obj in hidden:
        obj.visible_camera = False
    for obj in visible:
        obj.visible_camera = True
