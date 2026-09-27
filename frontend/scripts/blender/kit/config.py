"""路徑與共用設定：場景尺寸一律讀 frontend/src/lib/wardKit.json（與前端共用的單一來源）。"""

import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = SCRIPTS_DIR.parent.parent
KIT_JSON_PATH = FRONTEND_DIR / "src" / "lib" / "wardKit.json"
GLOBALS_CSS_PATH = FRONTEND_DIR / "src" / "app" / "globals.css"
BED_SPRITE_DIR = FRONTEND_DIR / "public" / "images" / "beds"
MODEL_OUT_DIR = FRONTEND_DIR / "public" / "models" / "ward"
CACHE_DIR = SCRIPTS_DIR / ".cache"


def load_json(path: Path) -> dict:
    """讀取 UTF-8 JSON 檔。"""
    return json.loads(path.read_text(encoding="utf-8"))


def load_kit() -> dict:
    """讀取場景模組設定（wardKit.json）。"""
    return load_json(KIT_JSON_PATH)


# 只含數字或字串的陣列收成一行，與 Prettier 的 JSON 格式一致
FLAT_ARRAY_PATTERN = re.compile(r"\[\s+([^\[\]{}]*?)\s+\]")


def save_kit(kit: dict) -> None:
    """寫回 wardKit.json；格式與 Prettier 一致，避免來回產生差異。"""
    text = json.dumps(kit, ensure_ascii=False, indent=2)
    text = FLAT_ARRAY_PATTERN.sub(lambda m: "[" + ", ".join(v.strip() for v in m.group(1).split(",")) + "]", text)
    KIT_JSON_PATH.write_text(text + "\n", encoding="utf-8")


def script_args() -> list[str]:
    """取得 Blender 指令列 `--` 之後的參數。"""
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
