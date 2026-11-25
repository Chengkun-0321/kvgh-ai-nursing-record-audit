"""稽核服務的固定流程：狀態、稽核週期的日期、錯誤轉換與持久化。LLM 一律 mock。"""

from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditCycle, AuditRunStatus, AvailabilityState, Verdict
from app.core.exceptions import (
    DayNotEndedError,
    LLMConnectionError,
    LLMNotConfiguredError,
    LLMOutputError,
    NotFoundError,
)
from app.crud import audit_run as audit_run_crud
from app.models.audit import AuditRun
from app.schemas.llm_structured import LLMRequest, RuleOutput
from app.services.audit import service as audit_service
from app.services.audit.context import build_audit_context
from app.services.audit.registry import RULE_REGISTRY
from app.services.audit.rules.base import AuditInput, Availability, not_applicable
from app.services.audit.rules.r03_admission_completeness import R03AdmissionCompleteness
from app.services.audit.service import DAY_NOT_ENDED_MESSAGE, AuditService
from app.services.hospital_data.source import HospitalDataSource
from app.services.llm import gateway
from tests.hospital_data_samples import AUDIT_P3_KEY
from tests.services.audit.helpers import make_result, payload_for
from tests.services.llm.gateway_helpers import create_config

ADMISSION_DAY = date(2025, 12, 31)
SELECTED_DAY = date(2026, 1, 2)
# 測試注入的「今天」：SELECTED_DAY 已結束，隔日（2026-01-03）起才是今天之後
TODAY = date(2026, 1, 3)


@pytest.fixture
def service(audit_hospital_data_source: HospitalDataSource) -> AuditService:
    return _service_on(audit_hospital_data_source, TODAY)


def _service_on(source: HospitalDataSource, today: date) -> AuditService:
    return AuditService(source, today=lambda: today)


def _fake_llm(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> list[LLMRequest]:
    """以假輸出取代 gateway；回傳被呼叫時收到的請求清單。"""
    requests: list[LLMRequest] = []

    async def fake(
        _session: AsyncSession, request: LLMRequest, output_schema: type[RuleOutput]
    ) -> Any:
        requests.append(request)
        if error is not None:
            raise error
        return make_result(payload_for(output_schema, payload or {}))

    monkeypatch.setattr(gateway, "complete_structured", fake)
    return requests


async def _checklist_record_id(source: HospitalDataSource) -> str:
    ctx = await build_audit_context(source, AUDIT_P3_KEY, None)
    return R03AdmissionCompleteness().build_input(ctx.for_date(ADMISSION_DAY)).records[0].record_id


async def _run_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(AuditRun)) or 0)


async def test_once_rule_is_keyed_to_admission_date_and_cites_checklist(
    service: AuditService,
    session: AsyncSession,
    audit_hospital_data_source: HospitalDataSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await create_config(session)
    record_id = await _checklist_record_id(audit_hospital_data_source)
    _fake_llm(
        monkeypatch,
        {
            "verdict": "WARNING",
            "summary": "個人病史未見填寫，請確認",
            "findings": [
                {
                    "item": "個人病史",
                    "verdict": "WARNING",
                    "message": "個人病史未見填寫，請確認",
                    "evidence": [{"record_id": record_id, "excerpt": "個人病史：沒有填寫"}],
                }
            ],
            "incomplete_items": ["個人病史"],
        },
    )

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert result.status == AuditRunStatus.COMPLETED
    assert result.verdict == Verdict.WARNING
    assert result.business_date == ADMISSION_DAY
    assert result.details == {"incomplete_items": ["個人病史"]}
    (finding,) = result.findings
    assert finding.evidence[0].record_id == record_id
    assert finding.evidence[0].field == "個人病史"
    assert await audit_run_crud.get_latest(session, AUDIT_P3_KEY, "R03", ADMISSION_DAY) is not None


async def test_llm_output_error_becomes_needs_review_not_pass(
    service: AuditService,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await create_config(session)
    _fake_llm(monkeypatch, error=LLMOutputError("格式錯誤"))

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert result.status == AuditRunStatus.COMPLETED
    assert result.verdict == Verdict.NEEDS_REVIEW


async def test_missing_model_config_raises_and_writes_nothing(
    service: AuditService, session: AsyncSession
) -> None:
    with pytest.raises(LLMNotConfiguredError):
        await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert await _run_count(session) == 0


async def test_connection_error_is_recorded_as_failed_with_safe_message(
    service: AuditService, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await create_config(session)
    _fake_llm(monkeypatch, error=LLMConnectionError("無法連線到 http://localhost:11434"))

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert result.status == AuditRunStatus.FAILED
    assert result.verdict is None
    assert result.status_reason == "無法連線到 http://localhost:11434"


async def test_unexpected_error_is_failed_without_exposing_its_message(
    service: AuditService, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await create_config(session)
    _fake_llm(monkeypatch, error=RuntimeError("虛構病歷內容 XYZ"))

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert result.status == AuditRunStatus.FAILED
    assert result.status_reason == audit_service.EXECUTION_FAILED_MESSAGE
    assert "XYZ" not in (result.status_reason or "")


async def test_data_unavailable_rule_writes_run_without_calling_llm(
    service: AuditService, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests = _fake_llm(monkeypatch)

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R05")

    assert result.status == AuditRunStatus.DATA_UNAVAILABLE
    assert result.status_reason is not None
    assert requests == []


class _NotApplicableRule(R03AdmissionCompleteness):
    """測試用：事件規則在當日沒有事件。"""

    code = "R06"
    cycle = AuditCycle.EVENT

    def check_availability(self, ctx: Any) -> Availability:
        return not_applicable("當日無會診")

    def build_input(self, ctx: Any) -> AuditInput:
        raise AssertionError("不適用時不應整理輸入")


async def test_not_applicable_event_writes_run_without_calling_llm(
    service: AuditService,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(RULE_REGISTRY, "R06", _NotApplicableRule())
    requests = _fake_llm(monkeypatch)

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R06")

    assert result.status == AuditRunStatus.NOT_APPLICABLE
    assert result.business_date == SELECTED_DAY
    assert requests == []


async def test_unknown_rule_is_not_found(service: AuditService, session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R99")


async def test_overview_shows_rules_dates_and_one_time_result_on_any_day(
    service: AuditService,
    session: AsyncSession,
    audit_hospital_data_source: HospitalDataSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await create_config(session)
    _fake_llm(monkeypatch, {"verdict": "PASS", "summary": "完整", "findings": []})
    await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    overview = await service.get_day_overview(session, AUDIT_P3_KEY, date(2026, 1, 1))

    rules = {rule.rule_code: rule for rule in overview.rules}
    assert list(rules) == [f"R0{number}" for number in range(1, 8)]
    assert (overview.previous_date, overview.next_date) == (None, SELECTED_DAY)
    assert rules["R03"].effective_business_date == ADMISSION_DAY
    # 入院規則已完成：仍可單項重新稽核，但一鍵稽核不納入；結果顯示在總覽
    assert rules["R03"].can_run is True
    assert rules["R03"].include_in_run_all is False
    assert rules["R03"].latest_run is not None
    assert rules["R05"].availability.state == AvailabilityState.DATA_UNAVAILABLE
    assert rules["R05"].can_run is False
    assert rules["R02"].effective_business_date == date(2026, 1, 1)


async def test_overview_for_date_without_patient_data_is_not_found(
    service: AuditService, session: AsyncSession
) -> None:
    with pytest.raises(NotFoundError):
        await service.get_day_overview(session, AUDIT_P3_KEY, date(2026, 3, 1))


async def test_rule_validation_message_is_kept_and_result_is_needs_review(
    service: AuditService, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """規則專屬驗證不過時，保留規則給的說明（模組常數），且絕不視為 PASS。"""
    payload = {
        "verdict": "WARNING",
        "summary": "摘要",
        "findings": [],
        "incomplete_items": ["不存在的項目"],
    }
    _fake_llm(monkeypatch, payload)

    run = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert run.status == AuditRunStatus.COMPLETED
    assert run.verdict == Verdict.NEEDS_REVIEW
    assert run.summary == "模型輸出的項目不在必要項目清單內，無法判定"


async def test_program_facts_are_stored_with_rule_specific_output(
    service: AuditService, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """規則在 build_input 算出的 facts 會與 LLM 的專屬欄位一起存進 details。"""
    original = R03AdmissionCompleteness.build_input

    def with_facts(rule: R03AdmissionCompleteness, ctx: Any) -> AuditInput:
        audit_input = original(rule, ctx)
        return AuditInput(audit_input.variables, audit_input.records, {"checked_items": 8})

    monkeypatch.setattr(R03AdmissionCompleteness, "build_input", with_facts)
    _fake_llm(monkeypatch, {"verdict": "PASS", "summary": "皆已填寫", "findings": []})

    run = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert run.details == {"checked_items": 8, "incomplete_items": []}


async def test_selected_today_is_not_auditable_and_run_writes_nothing(
    audit_hospital_data_source: HospitalDataSource,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """所選日期＝今天（尚未結束）：每項規則都不可稽核，run_rule 回 409 且不呼叫 LLM、不寫入。"""
    await create_config(session)
    requests = _fake_llm(monkeypatch)
    service = _service_on(audit_hospital_data_source, SELECTED_DAY)

    overview = await service.get_day_overview(session, AUDIT_P3_KEY, SELECTED_DAY)

    rules = {rule.rule_code: rule for rule in overview.rules}
    assert rules["R02"].availability.state == AvailabilityState.DAY_NOT_ENDED
    assert rules["R02"].availability.label == "當日尚未結束"
    assert rules["R02"].availability.reason == DAY_NOT_ENDED_MESSAGE
    assert rules["R02"].can_run is False
    # 入院規則的入院日已結束，但判斷依據是畫面所選日期，同樣不可稽核
    assert rules["R03"].effective_business_date == ADMISSION_DAY
    assert rules["R03"].can_run is False

    with pytest.raises(DayNotEndedError) as error:
        await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R02")

    assert error.value.status_code == 409
    assert error.value.message == DAY_NOT_ENDED_MESSAGE
    assert await _run_count(session) == 0
    assert requests == []


async def test_yesterday_is_auditable_once_today_moves_past_it(
    audit_hospital_data_source: HospitalDataSource,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await create_config(session)
    _fake_llm(monkeypatch, {"verdict": "PASS", "summary": "完整", "findings": []})
    service = _service_on(audit_hospital_data_source, SELECTED_DAY + timedelta(days=1))

    overview = await service.get_day_overview(session, AUDIT_P3_KEY, SELECTED_DAY)
    run = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    rules = {rule.rule_code: rule for rule in overview.rules}
    assert rules["R03"].can_run is True
    assert run.status == AuditRunStatus.COMPLETED


async def test_default_date_is_latest_ended_day(
    audit_hospital_data_source: HospitalDataSource, session: AsyncSession
) -> None:
    # 今天是 01-02：01-02 尚未結束，預設為已結束的最新一天 01-01
    on_second = _service_on(audit_hospital_data_source, SELECTED_DAY)
    overview = await on_second.get_day_overview(session, AUDIT_P3_KEY, None)
    assert overview.business_date == date(2026, 1, 1)

    # 今天是 01-03：01-02 已結束，預設為 01-02
    on_third = _service_on(audit_hospital_data_source, TODAY)
    overview = await on_third.get_day_overview(session, AUDIT_P3_KEY, None)
    assert overview.business_date == SELECTED_DAY


async def test_default_date_falls_back_to_latest_when_no_day_has_ended(
    audit_hospital_data_source: HospitalDataSource, session: AsyncSession
) -> None:
    # 今天是 01-01，兩天都未結束：退回最新一天 01-02（仍為不可稽核）
    service = _service_on(audit_hospital_data_source, date(2026, 1, 1))

    overview = await service.get_day_overview(session, AUDIT_P3_KEY, None)

    assert overview.business_date == SELECTED_DAY
    assert {rule.rule_code: rule for rule in overview.rules}["R02"].can_run is False


async def test_settled_admission_rule_can_rerun_but_not_in_run_all(
    service: AuditService,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await create_config(session)
    requests = _fake_llm(monkeypatch, {"verdict": "PASS", "summary": "完整", "findings": []})
    await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    overview = await service.get_day_overview(session, AUDIT_P3_KEY, SELECTED_DAY)
    rule = {item.rule_code: item for item in overview.rules}["R03"]
    assert rule.can_run is True
    assert rule.include_in_run_all is False
    assert rule.availability.state == AvailabilityState.AVAILABLE
    assert rule.latest_run is not None

    # 重新稽核新增一列，舊結果保留；總覽改顯示最新一列
    second = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert second.status == AuditRunStatus.COMPLETED
    assert await _run_count(session) == 2
    assert len(requests) == 2
    overview = await service.get_day_overview(session, AUDIT_P3_KEY, SELECTED_DAY)
    latest = {item.rule_code: item for item in overview.rules}["R03"].latest_run
    assert latest is not None
    assert latest.id == second.id


async def test_validation_failure_needs_review_stays_runnable(
    service: AuditService,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """模型輸出未通過驗證（NEEDS_REVIEW 且有原因）不算完成，一鍵稽核仍納入。"""
    await create_config(session)
    _fake_llm(
        monkeypatch,
        {
            "verdict": "WARNING",
            "summary": "摘要",
            "findings": [],
            "incomplete_items": ["不存在的項目"],
        },
    )
    first = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")
    assert first.verdict == Verdict.NEEDS_REVIEW

    overview = await service.get_day_overview(session, AUDIT_P3_KEY, SELECTED_DAY)
    rule = {item.rule_code: item for item in overview.rules}["R03"]
    assert rule.can_run is True
    assert rule.include_in_run_all is True

    _fake_llm(monkeypatch, {"verdict": "PASS", "summary": "完整", "findings": []})
    second = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert second.status == AuditRunStatus.COMPLETED
    assert second.verdict == Verdict.PASS
    assert await _run_count(session) == 2
