"""A8：R02 以 Strategy 登錄在 RULE_REGISTRY，runner 不得直接引用 R02。"""

import inspect

from arch_helpers import APP_ROOT

from app.core.enums import Engine
from app.services.audit.rules import RULE_REGISTRY
from app.services.audit.rules.r02_copy_paste import R02CopyPasteRule


def test_a8_r02_is_registered() -> None:
    """A8：RULE_REGISTRY["R02"] 是 R02CopyPasteRule。"""
    registered = RULE_REGISTRY["R02"]

    assert registered is R02CopyPasteRule


def test_a8_r02_satisfies_audit_rule_protocol() -> None:
    """A8：R02CopyPasteRule 滿足 AuditRule Protocol。

    code="R02"、engine=Engine.LLM，有 name、applies_to，
    evaluate 是 coroutine function。
    """
    rule = R02CopyPasteRule

    assert rule.code == "R02"
    assert rule.engine == Engine.LLM
    assert Engine.LLM == "llm"
    assert isinstance(rule.name, str)
    assert rule.name
    assert callable(rule.applies_to)
    assert inspect.iscoroutinefunction(rule.evaluate)


def test_a8_runner_does_not_reference_r02_directly() -> None:
    """A8：runner.py 不得出現 "R02"、'R02' 或 R02CopyPasteRule。"""
    runner_path = APP_ROOT / "services" / "audit" / "runner.py"

    source = runner_path.read_text(encoding="utf-8")

    assert '"R02"' not in source
    assert "'R02'" not in source
    assert "R02CopyPasteRule" not in source
