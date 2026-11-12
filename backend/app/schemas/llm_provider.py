"""服務類型目錄與設定精靈的輸入、輸出結構。

前端只依這些欄位渲染：欄位是否需要、顯示名稱、範例、上限與錯誤訊息都由後端決定。
"""

import uuid

from pydantic import BaseModel

from app.core.enums import (
    DraftField,
    FieldRequirement,
    LlmProvider,
    ModelListPlanKind,
    ProviderChoice,
    WizardStepId,
)


class LlmProviderOptionRead(BaseModel):
    """一種服務類型的顯示名稱與欄位規則。"""

    provider: LlmProvider
    choice: ProviderChoice
    label: str
    description: str
    api_key: FieldRequirement
    api_base: FieldRequirement
    default_api_base: str | None
    api_base_example: str | None
    api_key_example: str | None
    model_example: str


class ProviderChoiceRead(BaseModel):
    """設定精靈第 1 步的一個選項；`default_provider` 為選取後先套用的服務類型。"""

    choice: ProviderChoice
    label: str
    description: str
    default_provider: LlmProvider


class WizardStepRead(BaseModel):
    """設定精靈的一步。"""

    step_id: WizardStepId
    title: str


class LlmSettingLimitsRead(BaseModel):
    """設定頁需要顯示或限制輸入長度的上限。"""

    config_name_max_length: int
    model_max_length: int
    api_base_max_length: int
    api_key_max_length: int
    timeout_min_seconds: int
    timeout_max_seconds: int
    default_timeout_seconds: int
    timeout_hint: str
    chat_max_messages: int
    chat_max_message_chars: int
    chat_limit_reached_message: str
    system_prompt_max_chars: int


class LlmProviderCatalogRead(BaseModel):
    """設定頁所需的服務類型目錄、精靈步驟與上限。"""

    providers: list[LlmProviderOptionRead]
    choices: list[ProviderChoiceRead]
    wizard_steps: list[WizardStepRead]
    limits: LlmSettingLimitsRead


class SummaryRowRead(BaseModel):
    """設定摘要的一列。"""

    label: str
    value: str


class LlmConfigDraftCheck(BaseModel):
    """設定精靈目前的表單內容；欄位一律為字串，格式錯誤由後端逐欄回報。"""

    # 編輯中的設定（新增時為 null），用來判斷是否沿用已儲存的金鑰
    config_id: uuid.UUID | None = None
    # 只檢查該步驟負責的欄位；null 表示檢查全部
    step_id: WizardStepId | None = None
    name: str = ""
    provider: LlmProvider
    model: str = ""
    api_base: str = ""
    api_key: str = ""
    timeout_seconds: str = ""
    clear_api_key: bool = False


class FieldErrorRead(BaseModel):
    """一個欄位的錯誤訊息。"""

    field: DraftField
    message: str


class ModelListPlanRead(BaseModel):
    """如何查詢可用模型；`config_id` 為可沿用已儲存金鑰的設定。"""

    kind: ModelListPlanKind
    reason: str | None
    config_id: uuid.UUID | None


class LlmConfigDraftCheckRead(BaseModel):
    """表單檢查結果；`errors` 依畫面順序排列，第一個即為要移動焦點的欄位。"""

    is_valid: bool
    errors: list[FieldErrorRead]
    keeps_stored_api_key: bool
    # 同一服務類型的已儲存金鑰遮罩值（不受「移除金鑰」勾選影響）；沒有時為 null
    stored_api_key_hint: str | None
    suggested_name: str
    model_list: ModelListPlanRead
    summary_rows: list[SummaryRowRead]
