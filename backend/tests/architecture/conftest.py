"""架構測試共用 fixture。

工具 arch_helpers 以 importlib 依路徑載入並登錄到 sys.modules，
本目錄的測試可直接 import。
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_helpers() -> ModuleType:
    name = "arch_helpers"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


helpers = _load_helpers()


@pytest.fixture(scope="session")
def app_imports() -> dict[str, set[str]]:
    """{相對於 app/ 的 posix 路徑: import 的模組集合}；至少要讀到一個檔案。"""
    result: dict[str, set[str]] = helpers.build_import_map()
    assert result, f"找不到任何原始碼：{helpers.APP_ROOT}"
    return result
