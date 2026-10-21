"""R02 稽核測試的共用 fixture：虛構資料包副本與環境變數。

共用工具 r02_support 以 importlib 依路徑載入，
並登錄到 sys.modules，本目錄的測試可直接 import。
"""

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

from app.core.config import get_settings


def _load_support() -> ModuleType:
    name = "r02_support"
    if name in sys.modules:
        return sys.modules[name]
    tests_root = Path(__file__).resolve().parents[2]
    path = tests_root / "fixtures" / "daily_packages" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load_support()


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """虛構資料包副本（tmp_path / "mock"）。

    MOCK_DATA_DIR 指向副本，RAW_DATA_DIR 指向 tmp_path / "raw"。
    """
    root: Path = support.prepare_data_dirs(tmp_path, monkeypatch)
    yield root
    get_settings.cache_clear()
