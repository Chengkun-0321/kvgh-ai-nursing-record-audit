"""算圖引擎設定：Cycles（模組貼圖）與 Eevee（快速預覽）。"""

import bpy

from . import scene as scene_utils

EEVEE_ENGINES = ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT")


def _enable_gpu(render_scene: bpy.types.Scene, device: str) -> str:
    """啟用 GPU（macOS 為 METAL）；無法使用時退回 CPU，並回傳實際使用的裝置。"""
    if device == "CPU":
        render_scene.cycles.device = "CPU"
        return "CPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = device
    except TypeError:
        render_scene.cycles.device = "CPU"
        return "CPU"
    prefs.get_devices()
    for gpu in prefs.devices:
        gpu.use = True
    render_scene.cycles.device = "GPU"
    return device


def configure_cycles(render_scene: bpy.types.Scene, samples: int, device: str) -> str:
    """固定 seed 與取樣數，讓重複建置的結果一致；背景透明供後處理補邊。"""
    scene_utils.use_engine(render_scene, ("CYCLES",))
    render_scene.cycles.samples = samples
    render_scene.cycles.use_denoising = True
    render_scene.cycles.seed = 0
    render_scene.cycles.use_animated_seed = False
    render_scene.cycles.max_bounces = 8
    render_scene.render.film_transparent = True
    render_scene.render.image_settings.file_format = "PNG"
    render_scene.render.image_settings.color_mode = "RGBA"
    return _enable_gpu(render_scene, device)


def configure_eevee(render_scene: bpy.types.Scene, samples: int) -> None:
    """預覽用 Eevee；燈多時放大陰影緩衝。"""
    scene_utils.use_engine(render_scene, EEVEE_ENGINES)
    render_scene.eevee.taa_render_samples = samples
    if hasattr(render_scene.eevee, "use_raytracing"):
        render_scene.eevee.use_raytracing = True
    pool = render_scene.eevee.bl_rna.properties.get("shadow_pool_size")
    if pool:
        render_scene.eevee.shadow_pool_size = pool.enum_items[-1].identifier
    render_scene.render.film_transparent = True
    render_scene.render.image_settings.file_format = "PNG"
