"""「稽核中」登記：執行期間總覽回報稽核中、重複送出回 409，結束（含失敗）後一律除名。

LLM 一律 mock。
"""

import asyncio
from datetime import date
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.enums import AuditRunStatus
from app.core.exceptions import AuditAlreadyRunningError, LLMNotConfiguredError
from app.schemas.audit import AuditRuleStatusRead
from app.schemas.llm_structured import LLMRequest, RuleOutput
from app.services.audit.running import RunningAudits, RunningKey
from app.services.audit.service import AuditService
from app.services.hospital_data.source import HospitalDataSource
from app.services.llm import gateway
from tests.hospital_data_samples import AUDIT_P3_KEY
from tests.services.audit.helpers import make_result, payload_for
from tests.services.llm.gateway_helpers import create_config

ADMISSION_DAY = date(2025, 12, 31)
SELECTED_DAY = date(2026, 1, 2)
TODAY = date(2026, 1, 3)
# R03 是入院規則：登記與查詢都以入院日為準，從任何一天看都顯示稽核中
R03_KEY = RunningKey(AUDIT_P3_KEY, "R03", ADMISSION_DAY)


@pytest.fixture
def running() -> RunningAudits:
    """每個測試各自一份登記，不與整個行程共用的那份互相影響。"""
    return RunningAudits()


@pytest.fixture
def service(audit_hospital_data_source: HospitalDataSource, running: RunningAudits) -> AuditService:
    return AuditService(audit_hospital_data_source, today=lambda: TODAY, running=running)


class _BlockingLLM:
    """呼叫後停在 `release` 之前，模擬模型還在回應；`started` 在收到請求時設定。"""

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def __call__(
        self, _session: AsyncSession, _request: LLMRequest, output_schema: type[RuleOutput]
    ) -> Any:
        self.calls += 1
        self.started.set()
        await self.release.wait()
        payload = {"verdict": "PASS", "summary": "完整", "findings": []}
        return make_result(payload_for(output_schema, payload))


async def _r03_status(
    service: AuditService, session_factory: async_sessionmaker[AsyncSession]
) -> AuditRuleStatusRead:
    # 另開 session，模擬重新整理後的新請求；執行中的那個請求仍占用原本的 session
    async with session_factory() as other:
        overview = await service.get_day_overview(other, AUDIT_P3_KEY, SELECTED_DAY)
    return {rule.rule_code: rule for rule in overview.rules}["R03"]


def test_hold_registers_during_and_releases_after() -> None:
    running = RunningAudits()

    with running.hold(R03_KEY):
        assert running.is_running(R03_KEY)

    assert not running.is_running(R03_KEY)


def test_hold_releases_even_when_the_body_raises() -> None:
    running = RunningAudits()

    with pytest.raises(RuntimeError), running.hold(R03_KEY):
        raise RuntimeError

    assert not running.is_running(R03_KEY)


def test_second_hold_of_same_key_is_rejected_but_other_keys_are_not() -> None:
    running = RunningAudits()
    other_day = RunningKey(AUDIT_P3_KEY, "R03", SELECTED_DAY)

    with running.hold(R03_KEY):
        with pytest.raises(AuditAlreadyRunningError), running.hold(R03_KEY):
            pass
        with running.hold(other_day):
            assert running.is_running(other_day)

    assert not running.is_running(R03_KEY)


async def test_running_rule_is_reported_and_duplicate_run_is_rejected(
    service: AuditService,
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await create_config(session)
    llm = _BlockingLLM()
    monkeypatch.setattr(gateway, "complete_structured", llm)

    first = asyncio.create_task(service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03"))
    await llm.started.wait()

    running_status = await _r03_status(service, session_factory)
    assert running_status.is_running is True
    assert running_status.include_in_run_all is False
    with pytest.raises(AuditAlreadyRunningError):
        await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    llm.release.set()
    result = await first

    assert result.status == AuditRunStatus.COMPLETED
    assert llm.calls == 1
    done_status = await _r03_status(service, session_factory)
    assert done_status.is_running is False
    assert done_status.latest_run is not None


async def test_failed_run_is_released_and_can_run_again(
    service: AuditService,
    session: AsyncSession,
    running: RunningAudits,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await create_config(session)

    async def boom(*_args: Any) -> Any:
        raise RuntimeError

    monkeypatch.setattr(gateway, "complete_structured", boom)

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert result.status == AuditRunStatus.FAILED
    assert not running.is_running(R03_KEY)


async def test_missing_model_config_is_released(
    service: AuditService, session: AsyncSession, running: RunningAudits
) -> None:
    with pytest.raises(LLMNotConfiguredError):
        await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R03")

    assert not running.is_running(R03_KEY)
