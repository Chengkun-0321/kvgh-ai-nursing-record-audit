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


def _patient_list(business_date: str, entries: list[tuple[str, str, str]]) -> dict[str, object]:
    return {
        "資料日期": f"{business_date[:4]}-{business_date[4:6]}-{business_date[6:]}",
        "病房": WARD_CODE,
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
