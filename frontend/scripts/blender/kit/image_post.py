"""算圖後處理：把物件邊緣的顏色往透明區延伸（補邊），避免貼圖取樣時出現黑邊。"""

import numpy as np

NEIGHBOR_SHIFTS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _grow_once(rgb: np.ndarray, filled: np.ndarray) -> None:
    total = np.zeros_like(rgb)
    count = np.zeros(filled.shape, dtype=np.float32)
    for dy, dx in NEIGHBOR_SHIFTS:
        shifted_rgb = np.roll(rgb, (dy, dx), axis=(0, 1))
        shifted_filled = np.roll(filled, (dy, dx), axis=(0, 1))
        total += shifted_rgb * shifted_filled[..., None]
        count += shifted_filled
    grow = (~filled) & (count > 0)
    rgb[grow] = total[grow] / count[grow][:, None]
    filled |= grow


def dilate_edges(pixels: np.ndarray, iterations: int = 8, keep_alpha: bool = False) -> np.ndarray:
    """回傳補邊後的 RGBA；keep_alpha=False 時整張不透明（模組貼圖不需要 alpha）。"""
    rgb = pixels[..., :3].copy()
    filled = pixels[..., 3] > 0.01
    for _ in range(iterations):
        _grow_once(rgb, filled)
    alpha = pixels[..., 3:4] if keep_alpha else np.ones_like(pixels[..., 3:4])
    return np.concatenate([rgb, alpha], axis=-1)
