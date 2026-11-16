"""prompt 模板：缺少變數時直接失敗，不產生缺字的 prompt。"""

import jinja2
import pytest

from app.services.llm.prompt_loader import render_prompt


def test_missing_variable_fails_instead_of_rendering_blank() -> None:
    with pytest.raises(jinja2.UndefinedError):
        render_prompt("r03_admission_completeness", 1, {"checklist_block": "x"})


def test_missing_template_version_fails() -> None:
    with pytest.raises(jinja2.TemplateNotFound):
        render_prompt("r03_admission_completeness", 99, {})
