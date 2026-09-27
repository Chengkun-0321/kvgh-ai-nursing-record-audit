"""校準後的正交相機：只平移，不旋轉。"""

import bpy
import numpy as np

from . import view
from .geometry import to_blender

CAMERA_DISTANCE_M = 80.0
MARGIN_M = 0.4


def fit_camera(scene: bpy.types.Scene, kit: dict, corners: list, px_per_meter: float) -> bpy.types.Object:
    """建立相機並框住所有角點；解析度依每公尺像素換算。"""
    right, up, forward = view.view_basis(kit["view"]["yawDeg"], kit["view"]["pitchDeg"])
    points = np.array(corners, dtype=float)
    u, v = points @ right, points @ up
    width_m = u.max() - u.min() + 2 * MARGIN_M
    height_m = v.max() - v.min() + 2 * MARGIN_M
    center = right * (u.max() + u.min()) / 2 + up * (v.max() + v.min()) / 2
    camera_data = bpy.data.cameras.new("ward_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(width_m, height_m)
    camera_data.clip_start, camera_data.clip_end = 0.1, CAMERA_DISTANCE_M * 3
    camera = bpy.data.objects.new("ward_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = to_blender(*(center - forward * CAMERA_DISTANCE_M))
    camera.rotation_euler = view.blender_camera_rotation(kit["view"])
    scene.camera = camera
    scene.render.resolution_x = round(width_m * px_per_meter)
    scene.render.resolution_y = round(height_m * px_per_meter)
    return camera
