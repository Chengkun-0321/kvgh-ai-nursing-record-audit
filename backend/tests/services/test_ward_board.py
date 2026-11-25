"""病床總覽讀取稽核結果：狀態、進度、待處理發現與入院規則的入院日歸日。

稽核結果直接寫入 `audit_runs`（不呼叫 LLM）；資料來源為虛構的 W98 病房（一床、兩天）。
"""

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditRunStatus, BedBoardStatus, Verdict
from app.crud import audit_run as audit_run_crud
from app.models.audit import AuditFinding, AuditRun
from app.schemas.ward_board import WardBedBoardRead
from app.services.audit.service import AuditService
from app.services.hospital_data.source import HospitalDataSource
from app.services.ward_board import BedBoardQuery, get_ward_bed_board
from tests.hospital_data_samples import AUDIT_P3_KEY, AUDIT_WARD_CODE

BOARD_DAY = date(2026, 1, 1)
# 測試注入的「今天」：BOARD_DAY 已結束
BOARD_TODAY = date(2026, 1, 3)
ADMISSION_DAY = date(2025, 12, 31)
OLDER = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
NEWER = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)


async def _board(
    session: AsyncSession,
    source: HospitalDataSource,
    day: date | None = BOARD_DAY,
    today: date = BOARD_TODAY,
) -> WardBedBoardRead:
    query = BedBoardQuery(ward_code=AUDIT_WARD_CODE, business_date=day, today=lambda: today)
    return await get_ward_bed_board(session, source, query)


async def _add_run(
    session: AsyncSession,
    rule_code: str,
    business_date: date,
    status: AuditRunStatus,
    *,
    verdict: Verdict | None = None,
    findings: list[AuditFinding] | None = None,
    details: dict[str, object] | None = None,
    created_at: datetime = NEWER,
) -> None:
    run = AuditRun(
        rule_code=rule_code,
        patient_key=AUDIT_P3_KEY,
        business_date=business_date,
        status=status,
        verdict=verdict,
        summary=None,
        details=details,
        findings=findings or [],
        created_at=created_at,
    )
    await audit_run_crud.add(session, run)
    await session.commit()


def _finding(position: int, item: str, verdict: Verdict, message: str) -> AuditFinding:
    return AuditFinding(position=position, item=item, verdict=verdict, message=message, evidence=[])


async def test_without_runs_bed_is_not_audited_with_progress(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    board = await _board(session, audit_hospital_data_source)

    (bed,) = board.beds
    assert bed.status == BedBoardStatus.NOT_AUDITED
    assert bed.summary_text == "尚未稽核"
    assert bed.audited_rule_count == 0
    assert bed.audit_progress_text == f"已稽核 0／{bed.auditable_rule_count} 項"
    assert bed.auditable_rule_count > 0
    assert not bed.is_pending


async def test_admission_day_rule_counts_toward_board_day(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    # R03 是入院規則，結果記在入院日；查詢當日的病床總覽時仍應計入
    await _add_run(session, "R03", ADMISSION_DAY, AuditRunStatus.COMPLETED, verdict=Verdict.PASS)

    board = await _board(session, audit_hospital_data_source)

    (bed,) = board.beds
    assert bed.status == BedBoardStatus.PASS
    assert bed.audited_rule_count == 1
    assert bed.empty_findings_text == "今日稽核項目皆無待確認事項"


async def test_latest_failed_is_not_audited_and_replaces_older_completed(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    await _add_run(
        session,
        "R03",
        ADMISSION_DAY,
        AuditRunStatus.COMPLETED,
        verdict=Verdict.WARNING,
        findings=[_finding(0, "個人病史", Verdict.WARNING, "個人病史未見填寫")],
        created_at=OLDER,
    )
    await _add_run(session, "R03", ADMISSION_DAY, AuditRunStatus.FAILED, created_at=NEWER)

    board = await _board(session, audit_hospital_data_source)

    (bed,) = board.beds
    assert bed.status == BedBoardStatus.NOT_AUDITED
    assert bed.audited_rule_count == 0
    assert bed.pending_findings == []


async def test_newer_completed_replaces_older_warning(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    await _add_run(
        session,
        "R03",
        ADMISSION_DAY,
        AuditRunStatus.COMPLETED,
        verdict=Verdict.WARNING,
        findings=[_finding(0, "個人病史", Verdict.WARNING, "個人病史未見填寫")],
        created_at=OLDER,
    )
    await _add_run(session, "R03", ADMISSION_DAY, AuditRunStatus.COMPLETED, verdict=Verdict.PASS)

    board = await _board(session, audit_hospital_data_source)

    (bed,) = board.beds
    assert bed.status == BedBoardStatus.PASS
    assert bed.pending_findings == []


async def test_worst_verdict_wins_and_findings_sorted_by_severity(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    # R02 排在 R03 之前（規則順序），但 WARNING 的 R03 發現應排在前面（依嚴重度）
    await _add_run(
        session,
        "R02",
        BOARD_DAY,
        AuditRunStatus.COMPLETED,
        verdict=Verdict.NEEDS_REVIEW,
        findings=[_finding(0, "複製貼上", Verdict.NEEDS_REVIEW, "請確認是否為複製內容")],
    )
    await _add_run(
        session,
        "R03",
        ADMISSION_DAY,
        AuditRunStatus.COMPLETED,
        verdict=Verdict.WARNING,
        findings=[_finding(0, "個人病史", Verdict.WARNING, "個人病史未見填寫")],
    )

    board = await _board(session, audit_hospital_data_source)

    (bed,) = board.beds
    assert bed.status == BedBoardStatus.WARNING
    assert bed.summary_text == "需確認 1 項・無法判定 1 項"
    assert [finding.rule_code for finding in bed.pending_findings] == ["R03", "R02"]
    assert bed.is_pending
    assert board.status_counts[1].count == 1


async def test_progress_counts_only_completed_auditable_rules(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    await _add_run(session, "R03", ADMISSION_DAY, AuditRunStatus.COMPLETED, verdict=Verdict.PASS)
    await _add_run(session, "R02", BOARD_DAY, AuditRunStatus.FAILED)

    board = await _board(session, audit_hospital_data_source)

    (bed,) = board.beds
    assert bed.audited_rule_count == 1
    assert bed.audit_progress_text == f"已稽核 1／{bed.auditable_rule_count} 項"


async def test_r01_unmentioned_element_label_matches_patient_page(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    await _add_run(
        session,
        "R01",
        ADMISSION_DAY,
        AuditRunStatus.COMPLETED,
        verdict=Verdict.NEEDS_REVIEW,
        findings=[_finding(0, "主訴", Verdict.NEEDS_REVIEW, "入院經過未提及主訴")],
        details={"elements": [{"element": "主訴", "mentioned": False}]},
    )

    board = await _board(session, audit_hospital_data_source)
    patient_day = await AuditService(
        audit_hospital_data_source, today=lambda: BOARD_TODAY
    ).get_day_overview(session, AUDIT_P3_KEY, BOARD_DAY)

    (bed,) = board.beds
    (finding,) = bed.pending_findings
    assert finding.verdict_label == "未見紀錄"
    r01 = next(rule for rule in patient_day.rules if rule.rule_code == "R01")
    assert r01.latest_run is not None
    assert r01.latest_run.findings[0].verdict_label == finding.verdict_label


async def test_status_counts_and_pending_flag_for_warning_bed(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    await _add_run(
        session,
        "R03",
        ADMISSION_DAY,
        AuditRunStatus.COMPLETED,
        verdict=Verdict.WARNING,
        findings=[_finding(0, "個人病史", Verdict.WARNING, "個人病史未見填寫")],
    )

    board = await _board(session, audit_hospital_data_source)

    counts = {count.status: count.count for count in board.status_counts}
    assert counts[BedBoardStatus.WARNING] == 1
    assert counts[BedBoardStatus.NOT_AUDITED] == 0
    assert board.bed_count == 1
    assert board.beds[0].is_pending


async def test_default_board_date_is_latest_ended_day(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    # 今天是 01-02：01-02 尚未結束，預設為 01-01
    board = await _board(session, audit_hospital_data_source, day=None, today=date(2026, 1, 2))
    assert board.business_date == BOARD_DAY

    # 今天是 01-01：沒有已結束的日子，退回最新一天 01-02
    board = await _board(session, audit_hospital_data_source, day=None, today=date(2026, 1, 1))
    assert board.business_date == date(2026, 1, 2)


async def test_settled_admission_rule_still_counts_on_board_and_is_rerunnable(
    session: AsyncSession, audit_hospital_data_source: HospitalDataSource
) -> None:
    # 已完成的入院規則：病床總覽仍算「已稽核」；病患頁可單項重跑，但一鍵稽核不納入
    await _add_run(session, "R03", ADMISSION_DAY, AuditRunStatus.COMPLETED, verdict=Verdict.PASS)

    board = await _board(session, audit_hospital_data_source)
    patient_day = await AuditService(
        audit_hospital_data_source, today=lambda: BOARD_TODAY
    ).get_day_overview(session, AUDIT_P3_KEY, BOARD_DAY)

    (bed,) = board.beds
    assert bed.audited_rule_count == 1
    r03 = next(rule for rule in patient_day.rules if rule.rule_code == "R03")
    assert r03.can_run is True
    assert r03.include_in_run_all is False
