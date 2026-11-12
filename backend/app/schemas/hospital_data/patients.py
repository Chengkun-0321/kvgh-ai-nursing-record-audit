"""原始資料頁的病房、病人清單與病人摘要輸出結構。"""

from datetime import date, datetime

from pydantic import BaseModel

from app.core.enums import RawRecordCategory


class WardRead(BaseModel):
    """一個有院方資料的病房。"""

    ward_code: str
    display_name: str
    # 由舊到新
    business_dates: list[date]
    latest_business_date: date
    latest_patient_count: int


class WardListRead(BaseModel):
    """所有有院方資料的病房；`default_ward_code` 為首頁預設顯示的病房。"""

    default_ward_code: str
    wards: list[WardRead]


class WorkChecklistItemRead(BaseModel):
    """工作清單的一項（院方只提供「有填寫／沒有填寫」）。"""

    label: str
    value: str
    is_filled: bool


class WorkChecklistRead(BaseModel):
    """工作清單；取自病人最新一天的資料檔。"""

    items: list[WorkChecklistItemRead]
    filled_count: int
    total_count: int


class RawPatientSummaryRead(BaseModel):
    """原始資料頁病人清單的一列。"""

    patient_key: str
    bed_code: str
    admitted_at_text: str | None
    admitted_at: datetime | None
    first_business_date: date
    last_business_date: date
    # 是否出現在該病房最新一天的病人清單（否則可能已出院或轉出）
    is_current: bool
    work_checklist_filled_count: int
    work_checklist_total_count: int


class RawPatientListRead(BaseModel):
    """某病房所有日期出現過的病人，依床號排序。"""

    ward_code: str
    display_name: str
    latest_business_date: date
    patients: list[RawPatientSummaryRead]


class CategoryCountRead(BaseModel):
    """某類紀錄在所有日期合併後的筆數。"""

    category: RawRecordCategory
    label: str
    count: int


class RawPatientDetailRead(BaseModel):
    """原始資料頁上方的病人摘要。"""

    patient_key: str
    ward_code: str
    bed_code: str
    admitted_at_text: str | None
    admitted_at: datetime | None
    is_current: bool
    # 這位病人有資料檔的日期，由舊到新
    business_dates: list[date]
    work_checklist: WorkChecklistRead
    category_counts: list[CategoryCountRead]


class RawSourceRead(BaseModel):
    """病人某日資料檔的原文。"""

    patient_key: str
    business_date: date
    content: str
