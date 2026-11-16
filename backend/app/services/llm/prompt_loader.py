"""載入並渲染 Jinja2 prompt：`app/prompts/<prompt_name>/v<N>.j2`。

使用 StrictUndefined：模板引用了未提供的變數時直接失敗，不會悄悄產生缺字的 prompt。
prompt 內容為純文字（非 HTML），因此不做 autoescape。
"""

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Final

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

PROMPTS_DIR: Final = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(PROMPTS_DIR),
        undefined=StrictUndefined,
        autoescape=select_autoescape(default=False),
        keep_trailing_newline=True,
    )


def render_prompt(prompt_name: str, prompt_version: int, variables: Mapping[str, str]) -> str:
    """渲染指定版本的 prompt。

    Args:
        prompt_name: 目錄名稱，例如 `r03_admission_completeness`。
        prompt_version: 版本號，對應 `v<N>.j2`。
        variables: 模板變數；需涵蓋模板中所有引用的名稱。

    Returns:
        渲染後的 prompt 全文。

    Raises:
        jinja2.TemplateNotFound: 找不到該版本的模板。
        jinja2.UndefinedError: 模板引用了未提供的變數。
    """
    template = _environment().get_template(f"{prompt_name}/v{prompt_version}.j2")
    return template.render(**variables)
