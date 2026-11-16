"""病患稽核 API：總覽與單項執行的狀態碼、回應結構與錯誤訊息。LLM 一律 mock。"""

from collections.abc import AsyncIterator, Callable
from datetime import date
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_db, get_hospital_data_source, get_today_provider
from app.main import app
from app.services.audit.service import DAY_NOT_ENDED_MESSAGE
from app.services.hospital_data.source import HospitalDataSource
from app.services.llm import gateway
from tests.hospital_data_samples import AUDIT_P3_KEY
from tests.services.audit.helpers import make_result, payload_for
from tests.services.llm.gateway_helpers import create_config

BASE = f"/api/v1/patients/{AUDIT_P3_KEY}/audits"


@pytest.fixture
async def audit_client(
    session_factory: async_sessionmaker[AsyncSession],
    audit_hospital_data_source: HospitalDataSource,
) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as db_session:
            yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_hospital_data_source] = lambda: audit_hospital_data_source
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


async def test_overview_returns_all_rules_and_neighbor_dates(audit_client: AsyncClient) -> None:
    response = await audit_client.get(BASE, params={"business_date": "2026-01-01"})

    assert response.status_code == 200
    body = response.json()
    assert [rule["rule_code"] for rule in body["rules"]] == [f"R0{n}" for n in range(1, 8)]
    assert body["previous_date"] is None
    assert body["next_date"] == "2026-01-02"
    assert body["available_dates"] == ["2026-01-01", "2026-01-02"]
    assert body["bed_code"] == "W98-001"


async def test_overview_defaults_to_latest_date(audit_client: AsyncClient) -> None:
    response = await audit_client.get(BASE)

    assert response.json()["business_date"] == "2026-01-02"


async def test_overview_for_missing_date_is_404(audit_client: AsyncClient) -> None:
    response = await audit_client.get(BASE, params={"business_date": "2026-03-01"})

    assert response.status_code == 404
    assert "沒有院方資料" in response.json()["detail"]


async def test_overview_for_unknown_patient_is_404(audit_client: AsyncClient) -> None:
    response = await audit_client.get("/api/v1/patients/9999/audits")

    assert response.status_code == 404


async def test_invalid_patient_key_is_rejected(audit_client: AsyncClient) -> None:
    response = await audit_client.get("/api/v1/patients/bad-key!/audits")

    assert response.status_code == 422


async def test_run_without_active_model_is_409_and_writes_nothing(
    audit_client: AsyncClient,
) -> None:
    response = await audit_client.post(f"{BASE}/2026-01-02/rules/R03/runs")

    assert response.status_code == 409
    assert "尚未設定使用中的模型" in response.json()["detail"]


async def test_run_returns_201_with_result(
    audit_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session:
        await create_config(session)

    async def fake(_session: AsyncSession, _request: Any, output_schema: Any) -> Any:
        payload = {"verdict": "PASS", "summary": "入院評估各項皆已填寫", "findings": []}
        return make_result(payload_for(output_schema, payload))

    monkeypatch.setattr(gateway, "complete_structured", fake)

    response = await audit_client.post(f"{BASE}/2026-01-02/rules/R03/runs")

    assert response.status_code == 201
    body = response.json()
    assert body["rule_code"] == "R03"
    assert body["status"] == "COMPLETED"
    assert body["status_label"] == "已完成"
    assert body["verdict"] == "PASS"
    assert body["business_date"] == "2025-12-31"


async def test_unknown_rule_is_404_and_malformed_code_is_422(audit_client: AsyncClient) -> None:
    unknown = await audit_client.post(f"{BASE}/2026-01-02/rules/R99/runs")
    malformed = await audit_client.post(f"{BASE}/2026-01-02/rules/R3/runs")

    assert unknown.status_code == 404
    assert malformed.status_code == 422


async def test_run_for_date_without_patient_data_is_404(audit_client: AsyncClient) -> None:
    response = await audit_client.post(f"{BASE}/{date(2026, 3, 1)}/rules/R03/runs")

    assert response.status_code == 404


def _fixed_today(day: date) -> Callable[[], date]:
    return lambda: day


async def test_run_on_unended_day_is_409_with_reason(audit_client: AsyncClient) -> None:
    # 注入「今天」為 2026-01-02：所選日期尚未結束，應在呼叫 LLM 前回 409
    app.dependency_overrides[get_today_provider] = lambda: _fixed_today(date(2026, 1, 2))

    response = await audit_client.post(f"{BASE}/2026-01-02/rules/R03/runs")

    assert response.status_code == 409
    assert response.json()["detail"] == DAY_NOT_ENDED_MESSAGE
