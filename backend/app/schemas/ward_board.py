"""首頁病床總覽的輸出結構；彙總數字、狀態與顯示文字都由後端算好。"""

from datetime import date, datetime

from pydantic import BaseModel

from app.core.enums import AgeGroup, BedBoardStatus, Sex, Verdict


class PatientSummaryRead(BaseModel):
    """病床上的病患摘要；院方資料沒有的欄位為 null（目前姓名、性別、年齡、診斷皆無）。"""

    patient_key: str
    name: str | None
    sex: Sex | None
    age_years: int | None
    age_group: AgeGroup | None
    admission_date: date | None
    length_of_stay_days: int | None
    diagnosis: str | None


class AuditFindingSummaryRead(BaseModel):
    """一條規則的稽核結果摘要；完整 Evidence 於病患頁面呈現。"""

    rule_code: str
    verdict: Verdict
    verdict_label: str
    message: str
    recorded_at: datetime


class BedStatusRead(BaseModel):
    """一張病床的狀態。"""

    bed_code: str
    patient: PatientSummaryRead
    status: BedBoardStatus
    status_label: str
    # 床位卡片上的摘要，例：「缺漏 1 項・需確認 2 項」「尚未稽核」
    summary_text: str
    # 待處理病床：已稽核且最嚴重判定不是 PASS（狀態標籤只在這種床位上顯示）
    is_pending: bool
    # 依嚴重度排序、已排除 PASS 的稽核結果
    pending_findings: list[AuditFindingSummaryRead]
    # 沒有待處理稽核結果時，詳情清單顯示的文字
    empty_findings_text: str


class StatusCountRead(BaseModel):
    """狀態列上一種狀態的床數。"""

    status: BedBoardStatus
    label: str
    count: int


class WardBedBoardRead(BaseModel):
    """首頁病床總覽。"""

    ward_code: str
    display_name: str
    business_date: date
    bed_count: int
    pending_bed_count: int
    status_counts: list[StatusCountRead]
    beds: list[BedStatusRead]
