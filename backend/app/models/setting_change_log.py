"""設定變更操作紀錄（只記欄位名稱，不記 API key 等值）。"""

import uuid

from sqlalchemy import JSON, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import SETTING_ACTOR_MAX_LENGTH, SETTING_TARGET_MAX_LENGTH
from app.core.enums import SettingChangeAction
from app.db.base import Base, CreatedAtMixin, IdMixin

_ACTION_MAX_LENGTH = 16


class SettingChangeLog(IdMixin, CreatedAtMixin, Base):
    """一次設定變更。"""

    __tablename__ = "setting_change_logs"

    target_type: Mapped[str] = mapped_column(String(SETTING_TARGET_MAX_LENGTH))
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    action: Mapped[SettingChangeAction] = mapped_column(
        Enum(
            SettingChangeAction,
            native_enum=False,
            length=_ACTION_MAX_LENGTH,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    changed_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    # TODO(待決): 登入機制確定後記錄操作者，目前為空
    actor: Mapped[str | None] = mapped_column(String(SETTING_ACTOR_MAX_LENGTH))
