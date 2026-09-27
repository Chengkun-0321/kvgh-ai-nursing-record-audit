"""固定視角的正交投影數學，與前端 lib/wardProjection.ts 使用同一組公式。

座標系採前端（three.js）慣例：X 向右、Y 向上、+Z 朝相機（病房前方），單位公尺。
Blender 為 Z 向上，換算見 to_blender()。
"""

import math

import numpy as np


def view_basis(yaw_deg: float, pitch_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """回傳相機的 right、up、forward 單位向量（three.js 座標）。"""
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    right = np.array([math.cos(yaw), 0.0, -math.sin(yaw)])
    up = np.array([-math.sin(yaw) * math.sin(pitch), math.cos(pitch), -math.cos(yaw) * math.sin(pitch)])
    forward = np.array([-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), -math.cos(yaw) * math.cos(pitch)])
    return right, up, forward


def project_px(points: np.ndarray, view: dict, scale_px: float, origin_px: np.ndarray) -> np.ndarray:
    """把世界座標點投影成影像像素（y 向下）；origin_px 為世界原點所在像素。"""
    right, up, _ = view_basis(view["yawDeg"], view["pitchDeg"])
    local = np.stack([points @ right, -(points @ up)], axis=-1)
    return origin_px + local * scale_px


def to_blender(point: np.ndarray) -> tuple[float, float, float]:
    """three.js 座標 (x, y, z) 換成 Blender 座標 (x, -z, y)。"""
    return (float(point[0]), float(-point[2]), float(point[1]))


def blender_camera_rotation(view: dict) -> tuple[float, float, float]:
    """Blender 相機的 XYZ Euler：先俯角再繞 Z 轉 yaw，與前端相機一致。"""
    return (math.radians(90 - view["pitchDeg"]), 0.0, math.radians(view["yawDeg"]))
