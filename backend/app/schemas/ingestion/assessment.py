"""入院護理評估與每日身體評估（只驗證、不正規化；對照 patient-daily.schema.json）。"""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from app.schemas.ingestion.common import (
    IngestionModel,
    NonEmptyStr,
    NullableDateTime,
    NullableStr,
    StaffId,
)

MusclePowerValue = (
    Literal["5", "4", "3", "2", "1", "0", "無法評估", "鎮靜劑使用", "嬰兒期會翻身"] | None
)
UrinationAbnormalType = Literal[
    "頻尿",
    "尿失禁",
    "多尿",
    "少尿",
    "無尿",
    "血尿",
    "血液透析",
    "腹膜透析",
    "排尿困難",
    "排尿疼痛",
    "排尿燒灼感",
    "尿液混濁",
    "尿道(膀胱)造口",
    "留置導尿管",
    "茶色尿",
    "恥骨上壓痛",
    "肋脊角疼痛/壓痛",
    "急尿",
    "其他",
]
FallRiskFactor = Literal[
    "步態不穩",
    "過去一年曾跌倒",
    "主訴頭暈/眩暈",
    "行為混亂、躁動",
    "下床活動需協助且不尋求協助或無陪伴者",
    "下肢肌力0~4分",
]
FallRiskMedication = Literal[
    "鎮靜劑安眠藥",
    "降壓藥",
    "輕瀉藥",
    "降血糖藥",
    "抗精神病藥",
    "抗憂鬱劑",
    "抗癲癇藥",
    "抗巴金森氏症藥物",
    "肌肉鬆弛劑",
    "抗組織胺藥",
    "麻醉止痛藥",
    "利尿劑",
    "心血管用藥",
]
NormalOrAbnormal = Literal["正常", "異常"]
SkinSite = Literal["薦骨", "坐骨", "股骨粗隆", "足部", "頭頸部", "面部", "軀幹", "上下肢", "無"]


class Consciousness(IngestionModel):
    """意識（GCS／RASS）。"""

    measured_at: NullableDateTime
    scale: Literal["GCS", "RASS"]
    e: Literal["1", "2", "3", "4"] | None
    v: Literal["1", "2", "3", "4", "5", "T", "E", "A"] | None
    m: Literal["1", "2", "3", "4", "5", "6"] | None
    rass: Literal["+4", "+3", "+2", "+1", "0", "-1", "-2", "-3", "-4", "-5"] | None


class Pain(IngestionModel):
    """疼痛分數。"""

    scale: str
    score: Annotated[int, Field(ge=0, le=10)] | None
    unable_to_assess: bool


class TubeSummary(IngestionModel):
    """身評畫面上的管路文字。"""

    has_tube: bool
    description: NullableStr


class Pulse(IngestionModel):
    """脈搏。"""

    status: NormalOrAbnormal
    abnormal_types: list[Literal["不規律", "快", "慢"]]


class BreathSounds(IngestionModel):
    """呼吸音。"""

    status: NormalOrAbnormal
    abnormal_types: list[Literal["痰音", "哮喘音", "濕囉音"]]
    other: NullableStr


class Urination(IngestionModel):
    """泌尿。"""

    status: NormalOrAbnormal
    abnormal_types: list[UrinationAbnormalType]
    other: NullableStr


class MusclePower(IngestionModel):
    """四肢肌力。"""

    left_upper: MusclePowerValue
    right_upper: MusclePowerValue
    left_lower: MusclePowerValue
    right_lower: MusclePowerValue


class FallRisk(IngestionModel):
    """跌倒危險評估。"""

    unable_to_move: bool
    risk_factors: list[FallRiskFactor]
    medications: list[FallRiskMedication]
    score: Annotated[int, Field(ge=0, le=7)]
    high_risk: bool
    osteoporosis_high_risk: bool


class AssessmentItems(IngestionModel):
    """身體評估各項目；空白（未填）為 null。"""

    consciousness: Consciousness | None
    pain: Pain | None
    sleep: Literal["正常", "不易入睡", "早醒", "淺眠", "嗜睡", "無法評估"] | None
    airway: Literal["無", "氣管內管", "氣切"] | None
    tubes: TubeSummary | None
    pulse: Pulse | None
    limb_circulation: (
        Literal[
            "微血管快速填滿",
            "微血管延遲填滿(大於五秒)",
            "輕微水腫(無壓窩)",
            "中、重度水腫(有壓窩)",
        ]
        | None
    )
    breath_sounds: BreathSounds | None
    cough: Literal["無", "有", "無法評估"] | None
    sore_throat: Literal["無", "有", "無法評估"] | None
    bowel_sounds: Literal["正常", "過快", "過慢", "無腸音"] | None
    appetite: list[Literal["正常", "減少", "灌食", "NPO", "嘔吐"]] | None
    urination: Urination | None
    skin_pressure_prone_sites: list[SkinSite] | None
    muscle_power: MusclePower | None
    mobility: Literal["完全能動", "尚可自行翻身", "無法自行翻身", "不能動"] | None
    fall_risk: FallRisk | None


class DailyPhysicalAssessment(IngestionModel):
    """每日身體評估（一個班一筆）。"""

    record_id: NonEmptyStr
    assessed_at: AwareDatetime
    shift: Literal["day", "evening", "night"]
    author_id: StaffId
    last_modified_at: NullableDateTime
    items: AssessmentItems


class AdmissionSection(IngestionModel):
    """入院評估的一般區塊。"""

    completed: bool
    content: dict[str, object] | None


class PhysicalAssessmentContent(IngestionModel):
    """入院評估的身體評估內容。"""

    narrative: NullableStr
    items: AssessmentItems


class PhysicalAssessmentSection(IngestionModel):
    """入院評估的身體評估區塊。"""

    completed: bool
    content: PhysicalAssessmentContent | None


class AdmissionCourseContent(IngestionModel):
    """住院經過全文。"""

    text: str


class AdmissionCourseSection(IngestionModel):
    """入院評估的住院經過區塊。"""

    completed: bool
    content: AdmissionCourseContent | None


class NotIntroducedItem(IngestionModel):
    """未介紹的環境項目與原因。"""

    item: str
    reason: str


class EnvironmentContent(IngestionModel):
    """環境介紹內容。"""

    introduced_items: list[str]
    not_introduced: list[NotIntroducedItem]


class EnvironmentSection(IngestionModel):
    """入院評估的環境區塊。"""

    completed: bool
    content: EnvironmentContent | None


class AdmissionSections(IngestionModel):
    """入院評估固定 8 個區塊。"""

    basic_info: AdmissionSection
    personal_history: AdmissionSection
    nutrition: AdmissionSection
    daily_living: AdmissionSection
    physical_assessment: PhysicalAssessmentSection
    psychosocial: AdmissionSection
    admission_course: AdmissionCourseSection
    environment: EnvironmentSection


class AdmissionAssessment(IngestionModel):
    """入院護理評估。"""

    record_id: NonEmptyStr
    assessed_at: AwareDatetime
    author_id: StaffId
    last_modified_at: NullableDateTime
    sections: AdmissionSections
