"""時間軸合併、去重、篩選與檢驗矩陣。"""

from datetime import date

import pytest

from app.core.enums import AbnormalFlag, RawRecordCategory
from app.core.exceptions import InvalidInputError
from app.schemas.hospital_data.raw import RawPatientFile
from app.services.hospital_data.index import find_patient_history
from app.services.hospital_data.labs import (
    UNNAMED_ITEM_LABEL,
    LabRow,
    build_lab_matrix,
    extract_lab_rows,
    merge_lab_rows,
    parse_abnormal_flag,
)
from app.services.hospital_data.source import HospitalDataSource
from app.services.hospital_data.timeline import (
    TimelineFilter,
    build_lab_matrix_read,
    build_timeline,
    collect_events,
)
from tests.hospital_data_samples import P1_KEY, P2_KEY


def _categories(source: HospitalDataSource, patient_key: str) -> list[RawRecordCategory]:
    history = find_patient_history(source, patient_key)
    return [event.category for event in collect_events(source, history)]


def test_examination_repeated_across_days_is_deduplicated(
    hospital_data_source: HospitalDataSource,
) -> None:
    categories = _categories(hospital_data_source, P1_KEY)
    assert categories.count(RawRecordCategory.EXAMINATION) == 2


def test_duplicate_keeps_earliest_business_date(hospital_data_source: HospitalDataSource) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    exams = [
        e
        for e in collect_events(hospital_data_source, history)
        if e.category == RawRecordCategory.EXAMINATION and e.title == "胸部X光"
    ]
    assert [e.business_date for e in exams] == [date(2026, 1, 1)]


def test_no_record_string_yields_no_notes(hospital_data_source: HospitalDataSource) -> None:
    assert RawRecordCategory.NURSING_PROGRESS_NOTE not in _categories(hospital_data_source, P2_KEY)


def test_days_are_newest_first_and_filtered(hospital_data_source: HospitalDataSource) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    full = build_timeline(hospital_data_source, history, TimelineFilter())
    assert [d.day for d in full.days][:2] == [date(2026, 1, 2), date(2026, 1, 1)]

    day_2_only = TimelineFilter(start_date=date(2026, 1, 2), end_date=date(2026, 1, 2))
    filtered = build_timeline(hospital_data_source, history, day_2_only)
    assert [d.day for d in filtered.days] == [date(2026, 1, 2)]


def test_category_filter(hospital_data_source: HospitalDataSource) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    only_notes = TimelineFilter(categories=frozenset({RawRecordCategory.NURSING_PROGRESS_NOTE}))
    timeline = build_timeline(hospital_data_source, history, only_notes)
    assert timeline.event_count == 2
    assert {e.category for d in timeline.days for e in d.events} == {
        RawRecordCategory.NURSING_PROGRESS_NOTE
    }


def test_date_only_records_are_marked(hospital_data_source: HospitalDataSource) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    notes = [
        e
        for e in collect_events(hospital_data_source, history)
        if e.category == RawRecordCategory.NURSING_PROGRESS_NOTE
    ]
    assert all(note.is_date_only for note in notes)
    assert notes[0].tag == "交班"


def test_lab_event_counts_abnormal_values(hospital_data_source: HospitalDataSource) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    labs = [
        e
        for e in collect_events(hospital_data_source, history)
        if e.category == RawRecordCategory.LAB_RESULT
    ]
    first = labs[0]
    assert (first.title, first.abnormal_high_count, first.abnormal_low_count) == ("3 項", 1, 1)


def test_lab_matrix_aligns_cells_to_columns(hospital_data_source: HospitalDataSource) -> None:
    history = find_patient_history(hospital_data_source, P1_KEY)
    matrix = build_lab_matrix_read(hospital_data_source, history, TimelineFilter())
    assert [c.time_text for c in matrix.columns] == ["2026-01-01 06:00", "2026-01-02 06:00"]
    rows = {row.item: row for row in matrix.rows}
    assert [[v.value for v in cell] for cell in rows["WBC"].cells] == [["12.0"], ["9.0"]]
    assert rows["HGB"].cells[1] == []
    assert rows["HGB"].reference_ranges == ["12 < 參考值 < 16"]


def _lab_rows(records: list[dict[str, str]]) -> list[LabRow]:
    patient_file = RawPatientFile.model_validate({"檢驗報告": records})
    return extract_lab_rows(patient_file, date(2026, 1, 1))


def test_lab_matrix_keeps_all_results_in_same_cell() -> None:
    rows = merge_lab_rows(
        _lab_rows(
            [
                {"日期": "2026-01-01 06:00", "K": "3.0", "範圍": "3.5 < 參考值 < 5.1"},
                {"日期": "2026-01-01 06:00", "K": "4.0", "範圍": "3.4 < 參考值 < 5.0"},
            ]
        )
    )
    _, matrix_rows = build_lab_matrix(rows)
    assert [v.value for v in matrix_rows[0].cells[0]] == ["3.0", "4.0"]
    assert matrix_rows[0].reference_ranges == ["3.5 < 參考值 < 5.1", "3.4 < 參考值 < 5.0"]


def test_lab_dedupe_keeps_different_abnormal_flags() -> None:
    record = {"日期": "2026-01-01 06:00", "K": "3.0", "範圍": "3.5 < 參考值 < 5.1"}
    rows = _lab_rows([{**record, "異常值": "No"}, {**record, "異常值": "Yes (↓)"}])
    assert len(merge_lab_rows(rows)) == 2


def test_start_after_end_is_rejected() -> None:
    with pytest.raises(InvalidInputError):
        TimelineFilter(start_date=date(2026, 1, 2), end_date=date(2026, 1, 1))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("No", AbnormalFlag.NORMAL),
        ("Yes (↑)", AbnormalFlag.HIGH),
        ("Yes (↓)", AbnormalFlag.LOW),
        ("Yes", AbnormalFlag.ABNORMAL),
        ("其他", None),
        (None, None),
    ],
)
def test_parse_abnormal_flag(text: str | None, expected: AbnormalFlag | None) -> None:
    assert parse_abnormal_flag(text) == expected


def test_unnamed_lab_item_gets_readable_label() -> None:
    patient_file = RawPatientFile.model_validate(
        {"檢驗報告": [{"日期": "2026-01-01 06:00", "": "陰性"}]}
    )
    rows = extract_lab_rows(patient_file, date(2026, 1, 1))
    assert rows[0].result.item == UNNAMED_ITEM_LABEL
    assert rows[0].result.reference_range is None
