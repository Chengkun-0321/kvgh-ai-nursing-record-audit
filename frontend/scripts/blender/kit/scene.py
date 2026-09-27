"""場景初始化：清空、公尺單位、色彩管理與算圖引擎。"""

import bpy

# 用 Standard 而非 AgX／Filmic：網頁端以無光照材質直接顯示烘焙色，兩邊顏色才一致
VIEW_TRANSFORM = "Standard"


def reset_scene() -> bpy.types.Scene:
    """刪除所有物件與孤立資料，回傳乾淨的場景。"""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for block in list(blocks):
            blocks.remove(block)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.view_settings.view_transform = VIEW_TRANSFORM
    scene.view_settings.look = "None"
    return scene


def use_engine(scene: bpy.types.Scene, preferred: tuple[str, ...]) -> str:
    """依序嘗試算圖引擎；引擎名稱隨 Blender 版本改變，不寫死單一值。"""
    for engine in preferred:
        try:
            scene.render.engine = engine
            return engine
        except TypeError:
            continue
    raise RuntimeError(f"找不到可用的算圖引擎：{preferred}")


def set_world_color(scene: bpy.types.Scene, color: tuple, strength: float) -> None:
    """設定環境光（均勻色）。"""
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs[0].default_value = color
    background.inputs[1].default_value = strength
