"""匯入所有 model，讓 `Base.metadata` 與 Alembic autogenerate 能找到資料表。"""

from app.models.llm_config import LlmConfig
from app.models.llm_system_prompt import LlmSystemPrompt
from app.models.setting_change_log import SettingChangeLog

__all__ = ["LlmConfig", "LlmSystemPrompt", "SettingChangeLog"]
