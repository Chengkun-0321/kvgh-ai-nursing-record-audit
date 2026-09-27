"""路徑與共用設定：場景尺寸一律讀 frontend/src/lib/wardKit.<視角>.json（與前端共用的單一來源）。

病房有兩個視角（straight 正視、tilted 斜視），各自一份設定、一套 GLB 與一套病床去背圖；
所有腳本以 `--view straight|tilted` 選擇，預設 straight。
"""

import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = SCRIPTS_DIR.parent.parent
LIB_DIR = FRONTEND_DIR / "src" / "lib"
PUBLIC_DIR = FRONTEND_DIR / "public"
GLOBALS_CSS_PATH = FRONTEND_DIR / "src" / "app" / "globals.css"
CACHE_DIR = SCRIPTS_DIR / ".cache"

VIEW_IDS = ("straight", "tilted")
DEFAULT_VIEW = "straight"


def load_json(path: Path) -> dict:
    """讀取 UTF-8 JSON 檔。"""
    return json.loads(path.read_text(encoding="utf-8"))


def kit_json_path(view_id: str) -> Path:
    """視角設定檔路徑。"""
    if view_id not in VIEW_IDS:
        raise ValueError(f"未知的視角：{view_id}（可用 {', '.join(VIEW_IDS)}）")
    return LIB_DIR / f"wardKit.{view_id}.json"


def load_kit(view_id: str) -> dict:
    """讀取指定視角的場景模組設定。"""
    return load_json(kit_json_path(view_id))


def public_path(url_path: str) -> Path:
    """把前端網址路徑（/models/ward）換成 public/ 下的實際目錄。"""
    return PUBLIC_DIR / url_path.lstrip("/")


def model_dir(kit: dict) -> Path:
    """GLB 輸出目錄（依設定檔的 modelDir）。"""
    return public_path(kit["modelDir"])


def sprite_dir(kit: dict) -> Path:
    """病床去背圖目錄（依設定檔的 spriteDir）。"""
    return public_path(kit["spriteDir"])


def render_dir(kit: dict) -> Path:
    """算圖快取，兩個視角分開存放，避免互相覆蓋。"""
    return CACHE_DIR / "renders" / kit["id"]


def calibration_path(view_id: str) -> Path:
    """去背圖校準點位（人工標記）。"""
    return SCRIPTS_DIR / f"sprite_calibration.{view_id}.json"


def preview_blend_path(view_id: str) -> Path:
    """預覽組裝另存的 .blend。"""
    return CACHE_DIR / "preview" / f"ward-preview-{view_id}.blend"


# 只含數字或字串的陣列收成一行，與 Prettier 的 JSON 格式一致
FLAT_ARRAY_PATTERN = re.compile(r"\[\s+([^\[\]{}]*?)\s+\]")


def save_kit(kit: dict) -> None:
    """寫回該視角的設定檔；格式與 Prettier 一致，避免來回產生差異。"""
    text = json.dumps(kit, ensure_ascii=False, indent=2)
    text = FLAT_ARRAY_PATTERN.sub(lambda m: "[" + ", ".join(v.strip() for v in m.group(1).split(",")) + "]", text)
    kit_json_path(kit["id"]).write_text(text + "\n", encoding="utf-8")


def script_args() -> list[str]:
    """取得 Blender 指令列 `--` 之後的參數。"""
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def pop_view(args: list[str]) -> tuple[str, list[str]]:
    """從參數取出 `--view <id>`，回傳 (視角, 其餘參數)。"""
    if "--view" not in args:
        return DEFAULT_VIEW, args
    index = args.index("--view")
    return args[index + 1], args[:index] + args[index + 2 :]
