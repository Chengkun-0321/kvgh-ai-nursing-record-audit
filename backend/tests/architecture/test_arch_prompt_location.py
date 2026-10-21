"""A12：R02 prompt 的位置與渲染出口。"""

from arch_helpers import APP_ROOT, violations

from app.services.llm.prompt_loader import prompt_id

ImportMap = dict[str, set[str]]

PROMPT_LOADER = "services/llm/prompt_loader.py"


def test_a12_r02_prompt_template_exists() -> None:
    """A12：backend/app/prompts/r02_copy_paste/v1.j2 存在。"""
    template = APP_ROOT / "prompts" / "r02_copy_paste" / "v1.j2"

    assert template.is_file()


def test_a12_only_prompt_loader_imports_jinja2(app_imports: ImportMap) -> None:
    """A12：整個 app/ 只有 services/llm/prompt_loader.py 可 import jinja2。"""
    others = [file for file in app_imports if file != PROMPT_LOADER]

    found = violations(app_imports, others, ("jinja2",))

    assert PROMPT_LOADER in app_imports, "應讀到 prompt_loader.py"
    assert not found, "違規 import jinja2：\n" + "\n".join(found)


def test_a12_prompt_id_format() -> None:
    """A12：prompt_id("r02_copy_paste", "v1") 為 r02_copy_paste/v1。"""
    result = prompt_id("r02_copy_paste", "v1")

    assert result == "r02_copy_paste/v1"
