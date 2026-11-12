"""衍生結果的快取：院方更新檔案後失效、回應被修改不污染快取、併發讀取一致、不多配置。"""

import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.core.enums import RawRecordCategory
from app.schemas.hospital_data.timeline import LabeledValueRead, LabMatrixValueRead
from app.services.hospital_data import labs
from app.services.hospital_data.index import find_patient_history
from app.services.hospital_data.source import HospitalDataSource
from app.services.hospital_data.timeline import (
    TimelineFilter,
    build_lab_matrix_read,
    build_timeline,
    collect_events,
    count_events_by_category,
)
from tests.hospital_data_samples import DAY_2, P1_FILE, P1_KEY, WARD_CODE

_THREAD_COUNT = 8
_CALLS_PER_THREAD = 20
# 確保改寫後的修改時間一定與原本不同（不依賴檔案系統的時間精度）
_MTIME_STEP_NS = 1_000_000_000


def _rewrite_p1_day_2_note(root: Path, new_text: str) -> None:
    path = root / DAY_2 / WARD_CODE / P1_FILE
    content = json.loads(path.read_text(encoding="utf-8"))
    content["護理記錄"][0]["內容"] = new_text
    content["檢驗報告"][0]["WBC"] = "8.0"
    old_mtime_ns = path.stat().st_mtime_ns
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    os.utime(path, ns=(old_mtime_ns + _MTIME_STEP_NS, old_mtime_ns + _MTIME_STEP_NS))


def _note_texts(source: HospitalDataSource) -> list[str | None]:
    history = find_patient_history(source, P1_KEY)
    return [
        event.text
        for event in collect_events(source, history)
        if event.category == RawRecordCategory.NURSING_PROGRESS_NOTE
    ]


def _matrix_values(source: HospitalDataSource) -> list[str]:
    history = find_patient_history(source, P1_KEY)
    matrix = build_lab_matrix_read(source, history, TimelineFilter())
    return [value.value for row in matrix.rows for cell in row.cells for value in cell]


def test_modified_file_is_read_again(
    hospital_data_source: HospitalDataSource, tmp_path: Path
) -> None:
    assert "虛構衛教內容" in _note_texts(hospital_data_source)
    assert "9.0" in _matrix_values(hospital_data_source)

    # conftest 的 hospital_data_source 把資料寫在 tmp_path / "hospital_data"
    _rewrite_p1_day_2_note(tmp_path / "hospital_data", "更新後的虛構內容")

    texts = _note_texts(hospital_data_source)
    assert "更新後的虛構內容" in texts
    assert "虛構衛教內容" not in texts
    values = _matrix_values(hospital_data_source)
    assert "8.0" in values
    assert "9.0" not in values


def test_mutating_timeline_does_not_affect_next_call(
    hospital_data_source: HospitalDataSource,
) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    expected = build_timeline(hospital_data_source, history, TimelineFilter()).model_dump()

    polluted = build_timeline(hospital_data_source, history, TimelineFilter())
    for day in polluted.days:
        for event in day.events:
            event.title = "被改掉"
            event.fields.append(LabeledValueRead(label="多的", value="多的"))
            for field in event.fields:
                field.value = "被改掉"
            for result in event.lab_results:
                result.value = "被改掉"

    assert build_timeline(hospital_data_source, history, TimelineFilter()).model_dump() == expected


def test_mutating_lab_matrix_does_not_affect_next_call(
    hospital_data_source: HospitalDataSource,
) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    expected = build_lab_matrix_read(hospital_data_source, history, TimelineFilter()).model_dump()

    polluted = build_lab_matrix_read(hospital_data_source, history, TimelineFilter())
    for row in polluted.rows:
        row.reference_ranges.append("被改掉")
        row.cells[0].append(LabMatrixValueRead(value="被改掉", abnormal_flag=None))

    rebuilt = build_lab_matrix_read(hospital_data_source, history, TimelineFilter())
    assert rebuilt.model_dump() == expected


def test_concurrent_calls_return_same_timeline(hospital_data_source: HospitalDataSource) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    expected = build_timeline(hospital_data_source, history, TimelineFilter()).model_dump()

    def _build(_: int) -> dict[str, object]:
        return build_timeline(hospital_data_source, history, TimelineFilter()).model_dump()

    with ThreadPoolExecutor(max_workers=_THREAD_COUNT) as executor:
        results = list(executor.map(_build, range(_THREAD_COUNT * _CALLS_PER_THREAD)))
    assert all(result == expected for result in results)


def test_category_counts_match_collected_events(
    hospital_data_source: HospitalDataSource,
) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    events = collect_events(hospital_data_source, history)
    expected = Counter(event.category for event in events)
    assert count_events_by_category(hospital_data_source, history) == expected


def test_lab_matrix_allocates_one_row_per_item(
    hospital_data_source: HospitalDataSource, monkeypatch: pytest.MonkeyPatch
) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    calls: list[str] = []
    original = labs._empty_matrix_row

    def _counting_empty_row(row: labs.LabRow, column_count: int) -> object:
        calls.append(row.result.item)
        return original(row, column_count)

    monkeypatch.setattr(labs, "_empty_matrix_row", _counting_empty_row)
    matrix = build_lab_matrix_read(hospital_data_source, history, TimelineFilter())

    # WBC 有兩次結果，舊寫法會為第二次再配置一整列
    assert sorted(calls) == sorted(row.item for row in matrix.rows)
    assert len(calls) == len(set(calls))
