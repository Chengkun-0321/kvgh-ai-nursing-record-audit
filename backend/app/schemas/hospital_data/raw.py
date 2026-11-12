"""院方原始 JSON 的輸入結構：只驗證外形，欄位內容的轉換在 `services/hospital_data/`。

院方欄位名稱為中文，這裡以 alias 對應到 glossary 的英文名稱；不使用的欄位（如 HHISNUM）不讀入。
注意：病人檔的檔名格式為 `<HCASENO>_<HHISNUM>.json`，檔名只用來開檔，不得放進 API 回應、網址或 log。
"""

from pydantic import BaseModel, ConfigDict, Field, RootModel

# 院方的一筆紀錄：欄位名稱 → 原始字串值（欄位依區塊而異，檢驗報告的項目名稱為動態鍵）
RawRecord = dict[str, str]
# 病人檔各區塊的值：多數為紀錄陣列；入院經過為字串陣列；沒有資料時院方給字串（如「無記錄」）
RawSectionValue = list[RawRecord] | list[str] | str


class RawPatientListEntry(BaseModel):
    """patientlist.json 中的一位病人。"""

    model_config = ConfigDict(frozen=True, extra="ignore")

    bed_code: str = Field(alias="床號")
    patient_key: str = Field(alias="HCASENO")
    file_name: str = Field(alias="檔案")


class RawPatientList(BaseModel):
    """某日某病房的 patientlist.json。"""

    model_config = ConfigDict(frozen=True, extra="ignore")

    business_date_text: str = Field(alias="資料日期")
    ward_code: str = Field(alias="病房")
    patients: list[RawPatientListEntry] = Field(alias="病人名單")


class RawPatientFile(RootModel[dict[str, RawSectionValue]]):
    """一位病人某日的資料檔：區塊名稱（院方中文）→ 區塊內容。"""

    model_config = ConfigDict(frozen=True)

    def records(self, section_name: str) -> list[RawRecord]:
        """取得紀錄陣列；區塊不存在、為字串（無資料）或為字串陣列時回傳空陣列。"""
        value = self.root.get(section_name)
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def texts(self, section_name: str) -> list[str]:
        """取得字串陣列（入院經過）；不是字串陣列時回傳空陣列。"""
        value = self.root.get(section_name)
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]

    def first_record(self, section_name: str) -> RawRecord:
        """取得只有一筆的區塊（病人基本資料、工作清單）；沒有時回傳空 dict。"""
        records = self.records(section_name)
        return records[0] if records else {}
