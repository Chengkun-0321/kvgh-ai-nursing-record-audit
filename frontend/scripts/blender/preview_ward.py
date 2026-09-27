"""依床數組裝整個病房並用校準相機算圖，檢查模組拼接與去背圖是否協調。

執行：
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python frontend/scripts/blender/preview_ward.py -- --beds 10 --out <輸出.png> [--engine cycles]
同時另存 .blend 到 frontend/scripts/blender/.cache/preview/，可用 Blender 開啟檢視。
"""

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import config, glb_preview, layout, lighting, render_setup, scene  # noqa: E402
from kit.camera import fit_camera  # noqa: E402
from kit.geometry import to_blender  # noqa: E402
from kit.modules import build_module  # noqa: E402
from kit.props.bed_proxy import bed_proxy  # noqa: E402
from kit.sprites import add_sprite  # noqa: E402

PREVIEW_BLEND_PATH = config.CACHE_DIR / "preview" / "ward-preview.blend"
ENGINES = ("eevee", "cycles")


def parse_args() -> argparse.Namespace:
    """解析 `--` 之後的參數。"""
    parser = argparse.ArgumentParser(prog="preview_ward")
    parser.add_argument("--beds", type=int, default=10)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ppm", type=float, default=90.0, help="每公尺像素")
    parser.add_argument("--engine", choices=ENGINES, default="eevee")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--device", default="METAL")
    parser.add_argument("--source", choices=("live", "glb"), default="live", help="live＝即時建模打光；glb＝組裝匯出的模組（與網頁相同）")
    return parser.parse_args(config.script_args())


def place_modules(target: bpy.types.Collection, placements: list, kit: dict) -> None:
    """同一模組只建一次，以 collection instance 擺到各位置（與前端 instancing 相同概念）。"""
    sources = {module_id: build_module(module_id, kit) for module_id in {p.module_id for p in placements}}
    for placement in placements:
        empty = bpy.data.objects.new(placement.module_id, None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = sources[placement.module_id]
        empty.location = to_blender(placement.x, 0, placement.z)
        target.objects.link(empty)


def place_sprites(target: bpy.types.Collection, anchors: list, kit: dict, with_proxy: bool) -> None:
    """依床序輪流使用 24 張去背圖，讓預覽涵蓋各種判定光暈。"""
    sprites = sorted(config.BED_SPRITE_DIR.glob("*.webp"))
    for index, anchor in enumerate(anchors):
        add_sprite(target, sprites[(index * 5 + 3) % len(sprites)], anchor, kit)
        if with_proxy:
            bed_proxy(target, *anchor)


def assemble(ward: bpy.types.Collection, args: argparse.Namespace, kit: dict, grid: tuple[int, int]) -> None:
    """live：即時建模與打光；glb：匯入模組與床下陰影貼花，不需燈光。"""
    placements = layout.module_placements(*grid, kit)
    anchors = layout.bed_anchors(args.beds, grid[0], kit)
    if args.source == "glb":
        glb_preview.place_glb_modules(ward, placements, kit)
        glb_preview.place_bed_shadows(ward, anchors, kit)
    else:
        place_modules(ward, placements, kit)
        lighting.add_ward_lights(ward, kit, grid)
    place_sprites(ward, anchors, kit, with_proxy=args.source == "live")


def configure_render(render_scene: bpy.types.Scene, args: argparse.Namespace) -> None:
    """設定算圖引擎與取樣數。"""
    if args.engine == "cycles":
        render_setup.configure_cycles(render_scene, args.samples, args.device)
    else:
        render_setup.configure_eevee(render_scene, args.samples)


def main() -> None:
    """組裝、算圖、另存 .blend。"""
    args = parse_args()
    kit = config.load_kit()
    render_scene = scene.reset_scene()
    columns, rows = layout.ward_grid(args.beds, kit)
    ward = bpy.data.collections.new("ward")
    render_scene.collection.children.link(ward)
    assemble(ward, args, kit, (columns, rows))
    fit_camera(render_scene, kit, layout.scene_bounds(columns, rows, kit), args.ppm)
    configure_render(render_scene, args)
    render_scene.render.filepath = str(args.out)
    bpy.ops.render.render(write_still=True)
    PREVIEW_BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW_BLEND_PATH))
    print(f"[preview] {args.beds} 床 → {columns}×{rows}，輸出 {args.out}")


main()
