"""原始資料時間軸與檢驗矩陣的輸出結構；畫面只需依欄位渲染，不需再計算。"""

from datetime import date, datetime

from pydantic import BaseModel

from app.core.enums import AbnormalFlag, RawRecordCategory


class LabeledValueRead(BaseModel):
    """一個「項目：結果」欄位，項目名稱沿用院方原文。"""

    label: str
    value: str


class LabResultRead(BaseModel):
    """一個檢驗項目的結果；`abnormal_flag` 為 null 表示院方未提供異常標記。"""

    item: str
    value: str
    reference_range: str | None
    abnormal_flag: AbnormalFlag | None


class TimelineEventRead(BaseModel):
    """時間軸上的一筆紀錄。

    `time_text` 為院方原始時間字串；`occurred_at` 為解析後的台北時間，無法解析時為 null。
    `is_date_only` 表示院方只給日期（如護理記錄），畫面不應顯示時刻。
    """

    event_id: str
    category: RawRecordCategory
    category_label: str
    # 最早出現這筆紀錄的資料日期（同一筆紀錄可能在多天的檔案中重複出現）
    business_date: date
    time_text: str
    occurred_at: datetime | None
    is_date_only: bool
    tag: str | None
    title: str | None
    text: str | None
    fields: list[LabeledValueRead]
    lab_results: list[LabResultRead]
    abnormal_high_count: int
    abnormal_low_count: int


class TimelineDayRead(BaseModel):
    """同一天的紀錄，依時間由早到晚排列。"""

    day: date
    events: list[TimelineEventRead]


class PatientTimelineRead(BaseModel):
    """一位病人在指定範圍內的時間軸；`days` 由新到舊。"""

    patient_key: str
    start_date: date | None
    end_date: date | None
    event_count: int
    days: list[TimelineDayRead]


class LabMatrixColumnRead(BaseModel):
    """檢驗矩陣的一欄：一個採檢時間。"""

    time_text: str
    occurred_at: datetime | None


class LabMatrixValueRead(BaseModel):
    """檢驗矩陣一格中的一個結果。"""

    value: str
    abnormal_flag: AbnormalFlag | None


class LabMatrixRowRead(BaseModel):
    """檢驗矩陣的一列：一個檢驗項目。

    `cells` 與 `columns` 一一對應；沒有檢驗時為空陣列。同一採檢時間、同一項目有多個不同結果時
    全部列出，不互相覆蓋。`reference_ranges` 為此項目出現過的所有不同範圍（依出現順序）。
    """

    item: str
    reference_ranges: list[str]
    cells: list[list[LabMatrixValueRead]]


class LabMatrixRead(BaseModel):
    """項目 × 採檢時間的檢驗矩陣；欄位由舊到新，列依項目第一次出現的順序。"""

    patient_key: str
    start_date: date | None
    end_date: date | None
    columns: list[LabMatrixColumnRead]
    rows: list[LabMatrixRowRead]
