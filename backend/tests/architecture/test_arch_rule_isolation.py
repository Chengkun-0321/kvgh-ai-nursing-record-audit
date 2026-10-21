"""A3、A10：稽核規則不得存取 DB、外部服務、匯入流程與 gateway。"""

from arch_helpers import files_under, violations

ImportMap = dict[str, set[str]]

RULES_DIR = "services/audit/rules/"


def _rule_files(app_imports: ImportMap) -> list[str]:
    files = files_under(app_imports, RULES_DIR)
    assert f"{RULES_DIR}r02_copy_paste.py" in files, "應讀到 r02_copy_paste.py"
    return files


def test_a3_rules_must_not_touch_db_or_http(app_imports: ImportMap) -> None:
    """A3：rules/ 不得 import app.crud、app.db、httpx、sqlalchemy。"""
    files = _rule_files(app_imports)

    found = violations(app_imports, files, ("app.crud", "app.db", "httpx", "sqlalchemy"))

    assert not found, "rules/ 違規 import：\n" + "\n".join(found)


def test_a10_rules_must_not_import_ingestion_or_gateway(
    app_imports: ImportMap,
) -> None:
    """A10：rules/ 不得 import app.services.ingestion、app.services.llm.gateway。

    含 from app.services.llm import gateway 的寫法。
    """
    files = _rule_files(app_imports)

    found = violations(
        app_imports,
        files,
        ("app.services.ingestion", "app.services.llm.gateway"),
    )

    assert not found, "rules/ 違規 import：\n" + "\n".join(found)
