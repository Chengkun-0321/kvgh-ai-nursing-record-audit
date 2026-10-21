"""院內格式 v0.1.0 共用的基底與欄位型別。

對照 `docs/hospital-data-spec/*.schema.json`：
- 不允許多餘欄位（`additionalProperties: false`）
- 必填可為 null 的欄位不給預設值，缺少欄位即驗證失敗
- 日期時間必須帶時區
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

SCHEMA_VERSION = "0.1.0"

SchemaVersion = Literal["0.1.0"]
NonEmptyStr = Annotated[str, Field(min_length=1)]
# 院方人員代碼（去識別），不得放姓名
StaffId = NonEmptyStr
NullableStr = str | None
NullableDateTime = AwareDatetime | None
NullableDate = date | None
PatientStatus = Literal["inpatient", "transferred_out", "discharged"]


class IngestionModel(BaseModel):
    """院方資料的基底：嚴格型別、禁止多餘欄位、不可變。"""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
