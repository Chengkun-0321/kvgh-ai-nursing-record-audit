"""校準病床去背圖的視角，讓 3D 場景的正交相機與圖片透視一致。

原理：地面上互相垂直的兩組平行線（床寬方向、床長方向）在正交投影下的斜率，
只由 yaw 與 pitch 決定，與床的實際尺寸無關：
    寬向 dy/dx = tan(yaw)·sin(pitch)
    長向 dx/-dy = tan(yaw) / sin(pitch)
再以腳輪間距（假設值）做最小平方擬合，求出每公尺像素與床心錨點。

正視角（yaw 0）時上式無解（寬向斜率為 0），且生成的去背圖並非嚴格的正交投影，
所以改由校準檔的 `pitchDeg` 指定俯角（依床尾板正面與腳輪的比例目測），只擬合縮放與錨點。

執行（輸出疊圖到指定資料夾，加 --write 才會寫回 wardKit.<視角>.json）：
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python frontend/scripts/blender/calibrate_sprite.py -- <輸出資料夾> [--view straight|tilted] [--write]
"""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import config, image_io, view  # noqa: E402

CASTER_KEYS = ("casterFrontLeft", "casterFrontRight", "casterRearRight")
GRID_COLOR = (0.1, 0.55, 1.0)
CASTER_COLOR = (1.0, 0.1, 0.1)
POST_COLOR = (0.1, 0.75, 0.2)
POST_HEIGHT_M = 1.0
FLOOR_GRID_M = (3.0, 4.5)


def estimate_angles(points: dict) -> dict:
    """由寬向、長向線段斜率求 yaw 與 pitch（腳輪與床頭床尾板兩組平均）。"""
    px = {name: np.array(value, dtype=float) for name, value in points.items()}
    width_vectors = [
        px["casterFrontRight"] - px["casterFrontLeft"],
        px["footboardTopRight"] - px["footboardTopLeft"],
        px["headboardTopRight"] - px["headboardTopLeft"],
    ]
    board_axis = (px["headboardTopLeft"] + px["headboardTopRight"] - px["footboardTopLeft"] - px["footboardTopRight"]) / 2
    length_vectors = [px["casterRearRight"] - px["casterFrontRight"], board_axis]
    width_slope = float(np.mean([v[1] / v[0] for v in width_vectors]))
    length_lean = float(np.mean([v[0] / -v[1] for v in length_vectors]))
    tan_yaw = math.sqrt(width_slope * length_lean)
    return {"yawDeg": math.degrees(math.atan(tan_yaw)), "pitchDeg": math.degrees(math.asin(width_slope / tan_yaw))}


def resolve_angles(calibration: dict) -> dict:
    """斜視角由斜率推算；校準檔指定 pitchDeg 時為正視角（yaw 0）。"""
    if "pitchDeg" in calibration:
        return {"yawDeg": 0.0, "pitchDeg": float(calibration["pitchDeg"])}
    return estimate_angles(calibration["pointsPx"])


def caster_world(span: dict) -> dict[str, np.ndarray]:
    """左前、右前、右後腳輪的世界座標（床心在原點，床頭朝 -Z）。"""
    half_w, half_l = span["width"] / 2, span["length"] / 2
    return {
        "casterFrontLeft": np.array([-half_w, 0, half_l]),
        "casterFrontRight": np.array([half_w, 0, half_l]),
        "casterRearRight": np.array([half_w, 0, -half_l]),
    }


def fit_scale_and_anchor(calibration: dict, angles: dict) -> tuple[float, np.ndarray]:
    """最小平方求每公尺像素（scale）與床心像素（anchor）；只用圖上看得到的腳輪（正視角看不到後輪）。"""
    keys = [key for key in CASTER_KEYS if key in calibration["pointsPx"]]
    corners = caster_world(calibration["casterSpanM"])
    unit = view.project_px(np.array([corners[k] for k in keys]), angles, 1.0, np.zeros(2))
    measured = np.array([calibration["pointsPx"][k] for k in keys], dtype=float)
    rows = [[u[0], 1, 0] for u in unit] + [[u[1], 0, 1] for u in unit]
    solution, *_ = np.linalg.lstsq(np.array(rows), np.concatenate([measured[:, 0], measured[:, 1]]), rcond=None)
    return float(solution[0]), solution[1:]


def draw_overlay(canvas: np.ndarray, result: dict, span: dict) -> None:
    """畫 0.5 m 地面格線、腳輪矩形與 1 m 高的立柱，供人工比對。"""
    angles, scale, anchor = result["angles"], result["scale"], result["anchor"]
    project = lambda pts: view.project_px(np.array(pts, dtype=float), angles, scale, anchor)  # noqa: E731
    half_x, half_z = FLOOR_GRID_M[0] / 2, FLOOR_GRID_M[1] / 2
    for x in np.arange(-half_x, half_x + 0.01, 0.5):
        a, b = project([[x, 0, -half_z], [x, 0, half_z]])
        image_io.draw_segment(canvas, a, b, GRID_COLOR)
    for z in np.arange(-half_z, half_z + 0.01, 0.5):
        a, b = project([[-half_x, 0, z], [half_x, 0, z]])
        image_io.draw_segment(canvas, a, b, GRID_COLOR)
    corners = list(caster_world(span).values())
    rear_left = corners[0] * np.array([1, 1, -1])
    ring = project([*corners, rear_left, corners[0]])
    for a, b in zip(ring[:-1], ring[1:]):
        image_io.draw_segment(canvas, a, b, CASTER_COLOR)
    for corner in corners:
        a, b = project([corner, corner + [0, POST_HEIGHT_M, 0]])
        image_io.draw_segment(canvas, a, b, POST_COLOR)


def render_overlays(calibration: dict, result: dict, out_path: Path) -> Path:
    """把疊圖橫向拼接輸出成一張 PNG。"""
    tiles = []
    for name in calibration["overlaySprites"]:
        canvas = image_io.flatten_on(image_io.load_rgba(config.sprite_dir(result["kit"]) / name))
        draw_overlay(canvas, result, calibration["casterSpanM"])
        tiles.append(canvas)
    image_io.save_png(np.concatenate(tiles, axis=1), out_path)
    return out_path


def _number(value: float) -> float | int:
    """整數角度寫成 0 而不是 0.0，與手寫的 JSON 一致。"""
    return int(value) if float(value).is_integer() else value


def write_kit(calibration: dict, result: dict) -> None:
    """把校準結果寫回該視角設定檔的 view 與 sprite。"""
    kit = result["kit"]
    kit["view"]["yawDeg"] = _number(round(result["angles"]["yawDeg"], 1))
    kit["view"]["pitchDeg"] = _number(round(result["angles"]["pitchDeg"], 1))
    kit["sprite"]["planeWidthM"] = round(kit["sprite"]["widthPx"] / result["scale"], 3)
    kit["sprite"]["anchorPx"] = {"x": round(float(result["anchor"][0])), "y": round(float(result["anchor"][1]))}
    head = np.mean([calibration["pointsPx"]["headboardTopLeft"], calibration["pointsPx"]["headboardTopRight"]], axis=0)
    kit["sprite"]["labelAnchorPx"] = {"x": round(float(head[0])), "y": round(float(head[1]) - calibration["labelLiftPx"])}
    config.save_kit(kit)


def main() -> None:
    """校準、輸出疊圖，必要時寫回設定。"""
    view_id, args = config.pop_view(config.script_args())
    calibration = config.load_json(config.calibration_path(view_id))
    angles = resolve_angles(calibration)
    scale, anchor = fit_scale_and_anchor(calibration, angles)
    result = {"kit": config.load_kit(view_id), "angles": angles, "scale": scale, "anchor": anchor}
    print(f"[calibrate] {view_id} yaw={angles['yawDeg']:.2f} pitch={angles['pitchDeg']:.2f} px/m={scale:.1f} anchor={anchor.round(1)}")
    out_path = Path(args[0]) / f"sprite-calibration-{view_id}.png"
    print(f"[calibrate] overlay → {render_overlays(calibration, result, out_path)}")
    if "--write" in args:
        write_kit(calibration, result)
        print(f"[calibrate] 已寫回 {config.kit_json_path(view_id)}")


main()
