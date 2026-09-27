"""建置病房場景模組：逐一在病房環境中用 Cycles 算圖，投影成貼圖後匯出 GLB。

執行（輸出到設定檔 modelDir，例如正視角為 frontend/public/models/ward-straight/）：
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python frontend/scripts/blender/build_ward_kit.py -- [--view straight|tilted] [--only baySpine bedShadow] [--samples 256] [--device METAL]
"""

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import config, context, export, image_io, image_post, projection, render_setup, scene  # noqa: E402
from kit.geometry import box  # noqa: E402
from kit.props import part  # noqa: E402
from kit.props.bed_proxy import bed_proxy  # noqa: E402

BED_SHADOW_ID = "bedShadow"
# shadow catcher 比病床代理物每邊多出的範圍（公尺），容納柔和陰影的外緣
SHADOW_MARGIN_M = (0.38, 0.4)


def parse_args() -> argparse.Namespace:
    """解析 `--` 之後的參數。"""
    parser = argparse.ArgumentParser(prog="build_ward_kit")
    parser.add_argument("--view", choices=config.VIEW_IDS, default=config.DEFAULT_VIEW)
    parser.add_argument("--only", nargs="*", default=None, help="只建置指定模組 id")
    parser.add_argument("--out", type=Path, default=None, help="預設為設定檔的 modelDir")
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--device", default="METAL", help="METAL／CUDA／OPTIX／CPU")
    parser.add_argument("--ppm", type=float, default=200.0, help="貼圖每公尺像素（100% 縮放為 pxPerMeter）")
    return parser.parse_args(config.script_args())


def render_png(name: str, frame: projection.ScreenFrame, kit: dict, keep_alpha: bool) -> Path:
    """算圖後補邊，回傳最終貼圖路徑。"""
    render_scene = bpy.context.scene
    projection.place_camera(render_scene, kit, frame)
    renders = config.render_dir(kit)
    raw_path, final_path = renders / f"{name}-raw.png", renders / f"{name}.png"
    renders.mkdir(parents=True, exist_ok=True)
    render_scene.render.filepath = str(raw_path)
    bpy.ops.render.render(write_still=True)
    pixels = image_post.dilate_edges(image_io.load_rgba(raw_path), keep_alpha=keep_alpha)
    image_io.save_png(pixels, final_path)
    return final_path


def finalize(objects: list, origin: tuple, job: dict) -> None:
    """合併、剔除背面、投影 UV、移到模組原點、貼圖、匯出。"""
    kit, frame = job["kit"], job["frame"]
    joined = export.join_evaluated(objects, job["name"])
    export.cull_back_faces(joined, kit)
    projection.assign_projected_uvs(joined, kit, frame)
    export.move_origin(joined, *origin)
    export.assign_texture(joined, job["texture"], job["keep_alpha"])
    export.export_glb(joined, job["out"])


def build_module(module_id: str, kit: dict, args: argparse.Namespace) -> None:
    """在環境中只讓目標模組被相機看見，其餘模組仍提供陰影與反光。"""
    scene.reset_scene()
    render_setup.configure_cycles(bpy.context.scene, args.samples, args.device)
    ward = context.build_context_ward(kit)
    placement, objects = context.pick_target(ward, module_id, kit)
    targets = set(objects)
    projection.set_camera_visibility(objects, [o for o in context.all_objects(ward) if o not in targets])
    frame = projection.fit_frame(projection.world_vertices(objects), kit, args.ppm)
    texture = render_png(module_id, frame, kit, keep_alpha=False)
    job = {"kit": kit, "frame": frame, "name": module_id, "texture": texture, "keep_alpha": False}
    finalize(objects, (placement.x, placement.z), {**job, "out": args.out / kit["modules"][module_id]["file"]})


def build_bed_shadow(kit: dict, args: argparse.Namespace) -> None:
    """床下陰影：只讓病床代理物投影，落在 shadow catcher 上，輸出含 alpha 的貼花。"""
    scene.reset_scene()
    render_setup.configure_cycles(bpy.context.scene, args.samples, args.device)
    ward = context.build_context_ward(kit)
    placement, _ = context.pick_target(ward, "baySpine", kit)
    anchor = (placement.x + kit["bay"]["widthM"] / 2, placement.z + kit["bay"]["bedCenterM"])
    for obj in context.all_objects(ward):
        obj.visible_camera, obj.visible_shadow = False, False
    collection = bpy.context.scene.collection.children["context"]
    bed_proxy(collection, anchor, kit["bedProxy"])
    proxy, (mx, mz), (ax, az) = kit["bedProxy"], SHADOW_MARGIN_M, anchor
    hx, hz = proxy["halfWidthM"] + mx, proxy["halfLengthM"] + mz
    catcher = box("bed_shadow", (ax - hx, 0.0, az - hz), (ax + hx, 0.001, az + hz), part(collection, "floor"))
    catcher.is_shadow_catcher = True
    frame = projection.fit_frame(projection.world_vertices([catcher]), kit, args.ppm)
    texture = render_png(BED_SHADOW_ID, frame, kit, keep_alpha=True)
    job = {"kit": kit, "frame": frame, "name": BED_SHADOW_ID, "texture": texture, "keep_alpha": True}
    finalize([catcher], anchor, {**job, "out": args.out / kit["decals"][BED_SHADOW_ID]["file"]})


def main() -> None:
    """依序建置所有（或指定的）模組。"""
    args = parse_args()
    kit = config.load_kit(args.view)
    args.out = args.out or config.model_dir(kit)
    targets = args.only or [*kit["modules"], BED_SHADOW_ID]
    for module_id in targets:
        if module_id == BED_SHADOW_ID:
            build_bed_shadow(kit, args)
        else:
            build_module(module_id, kit, args)
        print(f"[kit] {module_id} 完成")


main()
