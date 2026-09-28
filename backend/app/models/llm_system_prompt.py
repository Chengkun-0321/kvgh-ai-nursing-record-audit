"""所有模型呼叫共用的 system prompt（只新增、不修改，每次儲存為一個新版本）。"""

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin


class LlmSystemPrompt(IdMixin, CreatedAtMixin, Base):
    """共用 system prompt 的一個版本；版本號最大者為目前使用的版本。"""

    __tablename__ = "llm_system_prompts"

    # 從 1 開始遞增；唯一約束讓兩人同時儲存時只有一方成功
    version: Mapped[int] = mapped_column(Integer, unique=True)
    # 空字串表示不使用 system prompt
    content: Mapped[str] = mapped_column(Text)
