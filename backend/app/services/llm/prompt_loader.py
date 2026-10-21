"""載入並渲染版本化的 Jinja2 prompt 模板（`app/prompts/<prompt_name>/<version>.j2`）。

整個 `app/` 只有本模組 import jinja2。prompt 是送給模型的純文字，不做 HTML 跳脫；
模板變數缺漏時直接報錯（StrictUndefined），避免送出不完整的 prompt。
"""

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Final

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

PROMPTS_DIR: Final = Path(__file__).resolve().parents[2] / "prompts"
_TEMPLATE_SUFFIX: Final = ".j2"


def prompt_id(prompt_name: str, version: str) -> str:
    """稽核結果記錄的 prompt 版本識別，例：`r02_copy_paste/v1`。"""
    return f"{prompt_name}/{version}"


def render_prompt(prompt_name: str, version: str, variables: Mapping[str, object]) -> str:
    """渲染指定版本的 prompt。

    Args:
        prompt_name: 模板資料夾名稱，例：`r02_copy_paste`。
        version: 版本，例：`v1`。
        variables: 模板變數。

    Returns:
        渲染後的 prompt。

    Raises:
        jinja2.TemplateNotFound: 模板不存在。
        jinja2.UndefinedError: 缺少模板變數。
    """
    template = _environment().get_template(f"{prompt_id(prompt_name, version)}{_TEMPLATE_SUFFIX}")
    return template.render(**variables)


@lru_cache
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(PROMPTS_DIR),
        undefined=StrictUndefined,
        # 純文字 prompt：所有副檔名都不自動跳脫（等同關閉 autoescape）
        autoescape=select_autoescape(
            enabled_extensions=(), default_for_string=False, default=False
        ),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
