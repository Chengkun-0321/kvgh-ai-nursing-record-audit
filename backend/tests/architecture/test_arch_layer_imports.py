"""A1：backend/app/ 分層 import 限制（依 docs/conventions/architecture.md）。"""

from arch_helpers import files_under, matches, violations

ImportMap = dict[str, set[str]]


def test_a1_api_must_not_import_crud_models_db(app_imports: ImportMap) -> None:
    """A1：api/ 不得 import app.crud、app.models、app.db。

    唯一例外：api/deps.py 提供 get_db，可 import app.db。
    """
    api_files = files_under(app_imports, "api/")
    others = [file for file in api_files if file != "api/deps.py"]

    found = violations(app_imports, others, ("app.crud", "app.models", "app.db"))
    found_deps = violations(app_imports, ["api/deps.py"], ("app.crud", "app.models"))

    assert api_files, "應讀到 app/api/ 下的檔案"
    assert not found, "api/ 違規 import：\n" + "\n".join(found)
    assert not found_deps, "api/deps.py 違規 import：\n" + "\n".join(found_deps)


def test_a1_services_must_not_import_api_or_fastapi(app_imports: ImportMap) -> None:
    """A1：services/ 不得 import app.api、fastapi。"""
    service_files = files_under(app_imports, "services/")

    found = violations(app_imports, service_files, ("app.api", "fastapi"))

    assert service_files, "應讀到 app/services/ 下的檔案"
    assert not found, "services/ 違規 import：\n" + "\n".join(found)


def test_a1_crud_must_not_import_services_api_schemas(app_imports: ImportMap) -> None:
    """A1：crud/ 不得 import app.services、app.api、app.schemas。"""
    crud_files = files_under(app_imports, "crud/")

    found = violations(app_imports, crud_files, ("app.services", "app.api", "app.schemas"))

    assert not found, "crud/ 違規 import：\n" + "\n".join(found)


def test_a1_schemas_must_not_import_models_crud_services(
    app_imports: ImportMap,
) -> None:
    """A1：schemas/ 不得 import app.models、app.crud、app.services。"""
    schema_files = files_under(app_imports, "schemas/")

    found = violations(app_imports, schema_files, ("app.models", "app.crud", "app.services"))

    assert not found, "schemas/ 違規 import：\n" + "\n".join(found)


def test_a1_core_only_imports_core_inside_app(app_imports: ImportMap) -> None:
    """A1：core/ 在 app 內只能 import app.core 的模組（標準庫與第三方不限）。"""
    core_files = files_under(app_imports, "core/")

    found = [
        f"{file}: {module}"
        for file in core_files
        for module in sorted(app_imports[file])
        if matches(module, "app") and not matches(module, "app.core")
    ]

    assert core_files, "應讀到 app/core/ 下的檔案"
    assert not found, "core/ 違規 import：\n" + "\n".join(found)
