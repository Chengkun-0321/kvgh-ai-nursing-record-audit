"""架構測試工具：以 ast 解析 backend/app/ 下所有 .py 的 import。

- 相對 import 依檔案所在套件換算成絕對模組名
- from X import Y 同時記錄 X 與 X.Y
  （例：from app.services.llm import gateway 視為 import 了 app.services.llm.gateway）

本檔不是測試檔，由同目錄的 conftest.py 以 importlib 載入。
"""

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = BACKEND_ROOT / "app"

ImportMap = dict[str, set[str]]


def _module_parts(path: Path) -> list[str]:
    parts = list(path.relative_to(BACKEND_ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return parts


def _resolve_from(path: Path, node: ast.ImportFrom) -> str:
    """把 ImportFrom 的模組換算成絕對模組名。"""
    if node.level == 0:
        return node.module or ""
    package = _module_parts(path)
    if path.name != "__init__.py":
        package = package[:-1]
    base = package[: len(package) - (node.level - 1)]
    if node.module:
        base = [*base, node.module]
    return ".".join(base)


def collect_imports(path: Path) -> set[str]:
    """回傳檔案中所有 import 的絕對模組名。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from(path, node)
            if base:
                names.add(base)
            names.update(
                f"{base}.{alias.name}" if base else alias.name
                for alias in node.names
                if alias.name != "*"
            )
    return names


def build_import_map() -> ImportMap:
    """{相對於 app/ 的 posix 路徑: import 的模組集合}。"""
    result: ImportMap = {}
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative = path.relative_to(APP_ROOT).as_posix()
        result[relative] = collect_imports(path)
    return result


def matches(module: str, prefix: str) -> bool:
    """module 等於 prefix，或是 prefix 底下的子模組。"""
    return module == prefix or module.startswith(prefix + ".")


def files_under(imports: ImportMap, directory: str) -> list[str]:
    """回傳 app/ 下某目錄（相對路徑，如 "api/"）內的檔案。"""
    return [file for file in imports if file.startswith(directory)]


def violations(imports: ImportMap, files: list[str], forbidden: tuple[str, ...]) -> list[str]:
    """列出 files 中 import 了 forbidden 任一前綴的「檔案: 模組」。"""
    found: list[str] = []
    for file in files:
        for module in sorted(imports[file]):
            if any(matches(module, prefix) for prefix in forbidden):
                found.append(f"{file}: {module}")
    return found
