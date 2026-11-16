"""稽核服務的固定流程：狀態、稽核週期的日期、錯誤轉換與持久化。LLM 一律 mock。"""

from datetime import date
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditCycle, AuditRunStatus, AvailabilityState, Verdict
from app.core.exceptions import (
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
from app.services.audit.service import AuditService
from app.services.hospital_data.source import HospitalDataSource
from app.services.llm import gateway
from tests.hospital_data_samples import AUDIT_P3_KEY
from tests.services.audit.helpers import make_result, payload_for
from tests.services.llm.gateway_helpers import create_config

ADMISSION_DAY = date(2025, 12, 31)
SELECTED_DAY = date(2026, 1, 2)


@pytest.fixture
def service(audit_hospital_data_source: HospitalDataSource) -> AuditService:
    return AuditService(audit_hospital_data_source)


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
    assert rules["R03"].can_run is True
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
