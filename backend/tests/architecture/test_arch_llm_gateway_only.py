"""A2：LLM 唯一出口；只有 services/llm/gateway.py 可 import litellm。"""

from arch_helpers import matches, violations

ImportMap = dict[str, set[str]]

GATEWAY = "services/llm/gateway.py"
CHATGPT_AUTH = "services/llm/chatgpt_auth.py"


def test_a2_only_gateway_imports_litellm(app_imports: ImportMap) -> None:
    """A2：gateway.py 與 chatgpt_auth.py 以外的檔案不得 import litellm。"""
    others = [file for file in app_imports if file not in (GATEWAY, CHATGPT_AUTH)]

    found = violations(app_imports, others, ("litellm",))

    assert GATEWAY in app_imports, "應讀到 app/services/llm/gateway.py"
    assert not found, "違規 import litellm：\n" + "\n".join(found)


def test_a2_chatgpt_auth_only_imports_litellm_chatgpt(app_imports: ImportMap) -> None:
    """A2：chatgpt_auth.py 只可 import litellm.llms.chatgpt 底下的模組。"""
    modules = app_imports.get(CHATGPT_AUTH, set())

    found = [
        module
        for module in sorted(modules)
        if matches(module, "litellm") and not matches(module, "litellm.llms.chatgpt")
    ]

    assert not found, "chatgpt_auth.py 違規 import：\n" + "\n".join(found)


def test_a2_no_model_sdk_imports(app_imports: ImportMap) -> None:
    """A2：整個 backend/app/ 不得 import openai、anthropic。"""
    found = violations(app_imports, list(app_imports), ("openai", "anthropic"))

    assert not found, "違規 import 模型 SDK：\n" + "\n".join(found)
