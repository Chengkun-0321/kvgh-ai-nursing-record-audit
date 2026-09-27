"""以 Blender 內建 numpy 讀寫圖片（系統不另裝 Pillow）。陣列一律為由上到下的 RGBA float。"""

from pathlib import Path

import bpy
import numpy as np


def load_rgba(path: Path) -> np.ndarray:
    """讀取圖片為 (H, W, 4) 陣列，第 0 列為影像最上方。"""
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(height, width, 4)[::-1].copy()
    bpy.data.images.remove(image)
    return pixels


def save_png(pixels: np.ndarray, path: Path) -> None:
    """把 (H, W, 4) 陣列存成 PNG。"""
    height, width = pixels.shape[:2]
    image = bpy.data.images.new(path.stem, width, height, alpha=True)
    image.pixels[:] = np.ascontiguousarray(pixels[::-1]).reshape(-1)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def flatten_on(pixels: np.ndarray, background: float = 0.88) -> np.ndarray:
    """去背圖疊到淺灰底，方便人工檢視疊圖。"""
    alpha = pixels[..., 3:4]
    rgb = pixels[..., :3] * alpha + background * (1 - alpha)
    return np.concatenate([rgb, np.ones_like(alpha)], axis=-1)


def draw_segment(canvas: np.ndarray, start: np.ndarray, end: np.ndarray, color: tuple) -> None:
    """在畫布上畫 2px 線段（取樣點法，檢視用途不需反鋸齒）。"""
    steps = int(max(abs(end - start).max(), 1) * 2)
    samples = np.linspace(start, end, steps).round().astype(int)
    height, width = canvas.shape[:2]
    for dx, dy in ((0, 0), (1, 0), (0, 1)):
        xs, ys = samples[:, 0] + dx, samples[:, 1] + dy
        keep = (xs >= 0) & (xs < width) & (ys >= 0) & (ys < height)
        canvas[ys[keep], xs[keep], :3] = color
