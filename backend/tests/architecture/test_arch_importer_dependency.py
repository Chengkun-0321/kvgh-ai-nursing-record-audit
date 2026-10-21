"""A9：importer 只依賴 DataSource Protocol，不直接使用 LocalFixtureSource。"""

from arch_helpers import APP_ROOT


def test_a9_importer_does_not_reference_local_source_or_mock_dir() -> None:
    """A9：importer.py 原始碼不含 LocalFixtureSource、MOCK_DATA_DIR。"""
    importer_path = APP_ROOT / "services" / "ingestion" / "importer.py"

    source = importer_path.read_text(encoding="utf-8")

    assert "LocalFixtureSource" not in source
    assert "MOCK_DATA_DIR" not in source
