"""測試用的虛構院方資料（依院方格式自編，內容與任何真實病人無關）。

W99 病房、兩天：
- P1 兩天都在，第 2 天「檢查」重複帶出第 1 天的紀錄，用來測跨日去重
- P2 只在第 1 天，護理記錄為字串「無記錄」
"""

import json
from pathlib import Path
from typing import Final

WARD_CODE: Final = "W99"
DAY_1: Final = "20260101"
DAY_2: Final = "20260102"
P1_KEY: Final = "1001"
P2_KEY: Final = "1002"
P1_FILE: Final = "1001_9001.json"
P2_FILE: Final = "1002_9002.json"

_EXAMINATION_DAY_1 = {
    "日期": "2026-01-01",
    "狀態": "正式報告",
    "項目": "胸部X光",
    "內容": "虛構報告",
}


def _patient_list(
    business_date: str, entries: list[tuple[str, str, str]], ward_code: str = WARD_CODE
) -> dict[str, object]:
    return {
        "資料日期": f"{business_date[:4]}-{business_date[4:6]}-{business_date[6:]}",
        "病房": ward_code,
        "病人數": len(entries),
        "病人名單": [
            {"床號": bed, "HCASENO": key, "HHISNUM": "0", "檔案": file_name}
            for bed, key, file_name in entries
        ],
    }


def _p1_day_1() -> dict[str, object]:
    return {
        "病人基本資料": [{"入院時間": "2025-12-30 10:00:00", "床號": "W99-001"}],
        "工作清單": [{"基本資料": "有填寫", "個人病史": "沒有填寫"}],
        "入院經過": ["虛構入院經過"],
        "護理記錄": [{"日期": "2026-01-01", "類別": "交班", "內容": "虛構交班內容"}],
        "生命徵象": [{"日期": "2026-01-01 08:00:00", "體溫": "36.5℃", "血壓": "120/80mmHg"}],
        "檢驗報告": [
            {
                "日期": "2026-01-01 06:00",
                "WBC": "12.0",
                "範圍": "3.5 < 參考值 < 11",
                "異常值": "Yes (↑)",
            },
            {
                "日期": "2026-01-01 06:00",
                "HGB": "10.0",
                "範圍": "12 < 參考值 < 16",
                "異常值": "Yes (↓)",
            },
            {"日期": "2026-01-01 06:00", "K": "4.0", "範圍": "3.5 < 參考值 < 5.1", "異常值": "No"},
        ],
        "檢查": [_EXAMINATION_DAY_1],
    }


def _p1_day_2() -> dict[str, object]:
    return {
        "病人基本資料": [{"入院時間": "2025-12-30 10:00:00", "床號": "W99-001"}],
        "工作清單": [{"基本資料": "有填寫", "個人病史": "有填寫"}],
        "護理記錄": [{"日期": "2026-01-02", "類別": "衛教指導", "內容": "虛構衛教內容"}],
        "檢驗報告": [
            {"日期": "2026-01-02 06:00", "WBC": "9.0", "範圍": "3.5 < 參考值 < 11", "異常值": "No"}
        ],
        "檢查": [
            _EXAMINATION_DAY_1,
            {"日期": "2026-01-02", "狀態": "初步報告", "項目": "超音波", "內容": "虛構報告"},
        ],
    }


def _p2_day_1() -> dict[str, object]:
    return {
        "病人基本資料": [{"入院時間": "2026-01-01 09:00:00", "床號": "W99-002"}],
        "工作清單": [{"基本資料": "沒有填寫"}],
        "護理記錄": "無記錄",
    }


def write_sample_hospital_data(root: Path) -> Path:
    """在 `root` 底下寫出虛構院方資料，回傳 `root`。"""
    files = {
        (DAY_1, "patientlist.json"): _patient_list(
            DAY_1, [("001", P1_KEY, P1_FILE), ("002", P2_KEY, P2_FILE)]
        ),
        (DAY_1, P1_FILE): _p1_day_1(),
        (DAY_1, P2_FILE): _p2_day_1(),
        (DAY_2, "patientlist.json"): _patient_list(DAY_2, [("001", P1_KEY, P1_FILE)]),
        (DAY_2, P1_FILE): _p1_day_2(),
    }
    for (business_date, file_name), content in files.items():
        path = root / business_date / WARD_CODE / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return root


# 稽核測試用的虛構病房：一位病人、兩天資料。入院日（2025-12-31）早於資料的第一天，
# 每日身評的時間是 2026-01-02，但第一天的檔案就已帶著它，用來測試依紀錄時間歸日（非資料夾日期）。
AUDIT_WARD_CODE: Final = "W98"
AUDIT_P3_KEY: Final = "2001"
AUDIT_P3_FILE: Final = "2001_9101.json"
_AUDIT_ADMITTED: Final = "2025-12-31 10:00:00"
_AUDIT_SNAPSHOT_ASSESSMENT: Final = {
    "身評時間": "2026-01-02 08:00:00",
    "呼吸音": "雙側呼吸音清，無囉音",
    "意識": "清楚",
}


def _audit_checklist() -> list[dict[str, str]]:
    return [
        {
            "基本資料": "有填寫",
            "個人病史": "沒有填寫",
            "營養評估": "有填寫",
            "日常生活": "有填寫",
            "身體評估": "有填寫",
            "心理評估": "有填寫",
            "環境": "有填寫",
        }
    ]


def _audit_day_1() -> dict[str, object]:
    return {
        "病人基本資料": [{"入院時間": _AUDIT_ADMITTED, "床號": "W98-001"}],
        "工作清單": _audit_checklist(),
        "入院經過": ["虛構入院經過段落"],
        "每日身評": [_AUDIT_SNAPSHOT_ASSESSMENT],
        "護理記錄": [{"日期": "2026-01-01", "類別": "交班", "內容": "虛構交班內容"}],
        "會診": [{"日期": "2026-01-01 09:00:00", "科別": "營養科"}],
    }


def _audit_day_2() -> dict[str, object]:
    return {
        "病人基本資料": [{"入院時間": _AUDIT_ADMITTED, "床號": "W98-001"}],
        "工作清單": _audit_checklist(),
        "每日身評": [_AUDIT_SNAPSHOT_ASSESSMENT],
        "護理記錄": [{"日期": "2026-01-02", "類別": "衛教指導", "內容": "虛構衛教內容"}],
    }


def write_audit_hospital_data(root: Path) -> Path:
    """在 `root` 底下寫出稽核測試用的虛構院方資料（W98），回傳 `root`。"""
    entry = [("001", AUDIT_P3_KEY, AUDIT_P3_FILE)]
    files = {
        (DAY_1, "patientlist.json"): _patient_list(DAY_1, entry, AUDIT_WARD_CODE),
        (DAY_2, "patientlist.json"): _patient_list(DAY_2, entry, AUDIT_WARD_CODE),
        (DAY_1, AUDIT_P3_FILE): _audit_day_1(),
        (DAY_2, AUDIT_P3_FILE): _audit_day_2(),
    }
    for (business_date, file_name), content in files.items():
        path = root / business_date / AUDIT_WARD_CODE / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return root
