"""從 globals.css 讀取 `--color-scene-*` 色票，讓 3D 模組與前端共用同一組顏色 token。"""

import re
from functools import cache

from . import config

TOKEN_PATTERN = re.compile(r"--color-scene-([a-z-]+):\s*#([0-9a-fA-F]{6})\s*;")


def srgb_to_linear(channel: float) -> float:
    """CSS 色碼為 sRGB，Blender 材質的 Base Color 需要線性值。"""
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


@cache
def scene_palette() -> dict[str, tuple[float, float, float, float]]:
    """回傳 {token 名稱: 線性 RGBA}；只收 6 碼 hex，含透明度的 token 不適用於實體材質。"""
    css = config.GLOBALS_CSS_PATH.read_text(encoding="utf-8")
    palette = {}
    for name, hex_code in TOKEN_PATTERN.findall(css):
        rgb = [srgb_to_linear(int(hex_code[i : i + 2], 16) / 255) for i in (0, 2, 4)]
        palette[name] = (*rgb, 1.0)
    return palette


def scene_color(name: str) -> tuple[float, float, float, float]:
    """取得單一場景色；token 不存在時直接報錯，避免默默用錯色。"""
    palette = scene_palette()
    if name not in palette:
        raise KeyError(f"globals.css 沒有 --color-scene-{name}")
    return palette[name]
