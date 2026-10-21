"""病患稽核 API 測試：B1、B2（合約）、B8（錯誤回應）、BR10、E1～E5、E10。

以 dependency override 注入指向 tmp_path 的 LocalFixtureSource
與假的 StructuredLLM，不發出網路請求。
"""

import importlib.util
import re
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.v1.endpoints.patient_audits import get_data_source, get_structured_llm
from app.core.config import get_settings
from app.core.exceptions import LLMNotConfiguredError
from app.main import app
from app.services.ingestion.sources import LocalFixtureSource


def _load_support() -> ModuleType:
    name = "r02_support"
    if name in sys.modules:
        return sys.modules[name]
    tests_root = Path(__file__).resolve().parents[2]
    path = tests_root / "fixtures" / "daily_packages" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load_support()
FakeLLM = support.FakeStructuredLLM

AUDIT_RUNS_URL = "/api/v1/audit-runs"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DAY_KEYS = {
    "business_date",
    "admission_id",
    "auditable",
    "not_auditable_reason",
    "latest_finding",
}
FINDING_KEYS = {
    "id",
    "audit_run_id",
    "rule_code",
    "patient_key",
    "business_date",
    "verdict",
    "message",
    "evidence",
    "note_similarities",
    "engine",
    "model",
    "prompt_version",
    "system_prompt_version",
    "audited_at",
}
EVIDENCE_KEYS = {"source", "record_id", "field", "recorded_at", "excerpt"}
SIMILARITY_KEYS = {
    "record_id",
    "recorded_at",
    "similar_record_id",
    "similar_business_date",
    "similarity_percent",
    "issue_types",
}
ISSUE_TYPES = {"copy", "unchanged", "clinical_changed", "outdated_reference"}

PATIENT_NOT_FOUND = "找不到此病患的資料"
DATE_NOT_FOUND = "此日期沒有該病患的資料"
FIRST_DAY_DETAIL = "入院首日無前日紀錄可比較"
NOT_CONFIGURED_DETAIL = "尚未設定使用中的模型，請至設定頁設定"

WARNING_0903_OUTPUT = support.llm_output(
    "WARNING",
    notes=[
        support.note(
            "NPN-P001-0903-01",
            similar_record_id="NPN-P001-0902-01",
            similarity_percent=98,
            issue_types=["copy"],
        )
    ],
    evidences=[support.evidence("NPN-P001-0903-01", support.P001_0903_EXCERPT)],
)
P001_0903 = {"patient_key": "P001", "business_date": "2026-09-03"}


@pytest.fixture
def mock_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """虛構資料包副本；MOCK_DATA_DIR、RAW_DATA_DIR 指向 tmp_path。"""
    root: Path = support.prepare_data_dirs(tmp_path, monkeypatch)
    yield root
    get_settings.cache_clear()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM(output=WARNING_0903_OUTPUT)


@pytest.fixture
async def api(
    client: AsyncClient, mock_root: Path, fake_llm: FakeLLM
) -> AsyncIterator[AsyncClient]:
    """覆寫資料來源與 StructuredLLM 的 API client；結束時移除自己加的覆寫。"""
    app.dependency_overrides[get_data_source] = lambda: LocalFixtureSource(mock_root)
    app.dependency_overrides[get_structured_llm] = lambda: fake_llm
    yield client
    app.dependency_overrides.pop(get_data_source, None)
    app.dependency_overrides.pop(get_structured_llm, None)


async def _count(factory: async_sessionmaker[AsyncSession], table: str) -> int:
    async with factory() as db_session:
        count: int = await support.count_rows(db_session, table)
        return count


async def _post(api: AsyncClient, body: dict[str, Any]) -> Response:
    return await api.post(AUDIT_RUNS_URL, json=body)


def _assert_safe_detail(response: Response, expected: str) -> None:
    """B8：detail 為繁中原字串，不含任何護理紀錄 content 的片段。"""
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert detail == expected
    for content in support.all_note_contents():
        assert content[:8] not in detail


def _parse_aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    return parsed


# ---------- B1 ----------


async def test_b1_audit_days_contract(api: AsyncClient) -> None:
    """B1：GET audit-days → 200，鍵恰好符合合約，days 由新到舊。"""
    response = await api.get("/api/v1/patients/P001/audit-days")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"patient_key", "days"}
    assert body["patient_key"] == "P001"
    dates = [day["business_date"] for day in body["days"]]
    assert dates == sorted(dates, reverse=True)
    assert len(dates) == 4
    for day in body["days"]:
        assert set(day) == DAY_KEYS
        assert DATE_PATTERN.match(day["business_date"])
        assert isinstance(day["auditable"], bool)


async def test_b1_latest_finding_has_finding_keys(api: AsyncClient) -> None:
    """B1：有結果時 latest_finding 的鍵與 B2 回應相同。"""
    await _post(api, P001_0903)

    response = await api.get("/api/v1/patients/P001/audit-days")

    days = {day["business_date"]: day for day in response.json()["days"]}
    assert set(days["2026-09-03"]["latest_finding"]) == FINDING_KEYS


# ---------- B2 ----------


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({}, id="B2-rule-code-omitted"),
        pytest.param({"rule_code": "R02"}, id="B2-rule-code-R02"),
    ],
)
async def test_b2_audit_run_contract(api: AsyncClient, extra: dict[str, str]) -> None:
    """B2：POST audit-runs → 201，回應鍵恰好符合合約；省略 rule_code 預設 R02。"""
    body = {**P001_0903, **extra}

    response = await _post(api, body)

    assert response.status_code == 201
    finding = response.json()
    assert set(finding) == FINDING_KEYS
    assert finding["rule_code"] == "R02"
    assert finding["patient_key"] == "P001"
    assert finding["business_date"] == "2026-09-03"
    assert finding["engine"] == "llm"
    assert finding["verdict"] in {"PASS", "WARNING", "NEEDS_REVIEW"}
    assert isinstance(finding["message"], str)
    uuid.UUID(str(finding["id"]))
    uuid.UUID(str(finding["audit_run_id"]))
    _parse_aware(finding["audited_at"])


async def test_b2_evidence_and_similarity_item_keys(api: AsyncClient) -> None:
    """B2：evidence 與 note_similarities 每項的鍵恰好符合合約。

    issue_types 的值屬於 copy／unchanged／clinical_changed／outdated_reference。
    """
    response = await _post(api, P001_0903)

    finding = response.json()
    assert finding["evidence"], "有效 Evidence 應被保留"
    for item in finding["evidence"]:
        assert set(item) == EVIDENCE_KEYS
    assert finding["note_similarities"], "當日每筆紀錄都應有 note_similarities"
    for item in finding["note_similarities"]:
        assert set(item) == SIMILARITY_KEYS
        assert set(item["issue_types"]) <= ISSUE_TYPES


# ---------- BR10 ----------


async def test_br10_each_post_adds_run_and_finding(
    api: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """BR10：對同一天 POST 兩次 → audit_runs、audit_findings 各 2 筆。

    兩次回傳的 id 不同；audit_runs 的規則代碼、業務日期、模型、
    開始與結束時間都有值。
    """
    first = await _post(api, P001_0903)
    second = await _post(api, P001_0903)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert await _count(session_factory, "audit_runs") == 2
    assert await _count(session_factory, "audit_findings") == 2
    query = text("SELECT rule_code, business_date, model, started_at, finished_at FROM audit_runs")
    async with session_factory() as db_session:
        rows = (await db_session.execute(query)).all()
    for row in rows:
        assert all(value is not None for value in row)
        assert row[0] == "R02"


async def test_br10_latest_finding_is_newest(api: AsyncClient) -> None:
    """BR10：audit-days 該日 latest_finding 為第二次的結果；其他日期仍為 null。"""
    await _post(api, P001_0903)
    second = await _post(api, P001_0903)

    response = await api.get("/api/v1/patients/P001/audit-days")

    days = {day["business_date"]: day for day in response.json()["days"]}
    assert days["2026-09-03"]["latest_finding"]["id"] == second.json()["id"]
    for key in ("2026-09-05", "2026-09-02", "2026-09-01"):
        assert days[key]["latest_finding"] is None


# ---------- E1 ----------


async def test_e1_unknown_patient_get_404(api: AsyncClient) -> None:
    """E1／B8：GET 不存在的 patient_key → 404「找不到此病患的資料」。"""
    response = await api.get("/api/v1/patients/NOPE/audit-days")

    assert response.status_code == 404
    _assert_safe_detail(response, PATIENT_NOT_FOUND)


async def test_e1_unknown_patient_post_404(api: AsyncClient) -> None:
    """E1／B8：POST 不存在的 patient_key → 404，同一 detail。"""
    body = {"patient_key": "NOPE", "business_date": "2026-09-03"}

    response = await _post(api, body)

    assert response.status_code == 404
    _assert_safe_detail(response, PATIENT_NOT_FOUND)


# ---------- E2、E10 ----------


async def test_e2_date_without_package_404(api: AsyncClient) -> None:
    """E2／B8：P001 + 2026-09-04（缺資料包）→ 404「此日期沒有該病患的資料」。"""
    body = {"patient_key": "P001", "business_date": "2026-09-04"}

    response = await _post(api, body)

    assert response.status_code == 404
    _assert_safe_detail(response, DATE_NOT_FOUND)


async def test_e10_missing_manifest_date_post_404(api: AsyncClient, mock_root: Path) -> None:
    """E10／E2：刪除 9/03 的 manifest 後 POST P001 9/03 → 404。"""
    (mock_root / "20260903" / "manifest.json").unlink()

    response = await _post(api, P001_0903)

    assert response.status_code == 404
    _assert_safe_detail(response, DATE_NOT_FOUND)


# ---------- E3 ----------


def _body(patient_key: str = "P001", business_date: str = "2026-09-02") -> dict[str, str]:
    return {"patient_key": patient_key, "business_date": business_date}


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(_body(business_date="2026-02-30"), id="E3-feb-30"),
        pytest.param(_body(business_date="2026/09/02"), id="E3-slash-date"),
        pytest.param(_body(business_date="abc"), id="E3-abc"),
        pytest.param(_body(patient_key=""), id="E3-empty-key"),
        pytest.param(_body(patient_key="P" * 65), id="E3-key-65-chars"),
        pytest.param({**_body(), "rule_code": "R01"}, id="E3-rule-R01"),
        pytest.param({**_body(), "rule_code": "r02"}, id="E3-rule-lowercase"),
    ],
)
async def test_e3_invalid_input_422(api: AsyncClient, body: dict[str, str]) -> None:
    """E3：日期不合法、patient_key 為空或超過 64 字元、rule_code 不是 R02 → 422。"""
    response = await _post(api, body)

    assert response.status_code == 422


async def test_e3_patient_key_64_chars_is_not_422(api: AsyncClient) -> None:
    """E3 邊界：patient_key 剛好 64 字元不是 422（不存在的病患 → 404）。"""
    response = await _post(api, _body(patient_key="P" * 64))

    assert response.status_code == 404
    _assert_safe_detail(response, PATIENT_NOT_FOUND)


async def test_e3_get_path_key_65_chars_422(api: AsyncClient) -> None:
    """E3：GET 路徑的 patient_key 為 65 字元 → 422。"""
    response = await api.get(f"/api/v1/patients/{'P' * 65}/audit-days")

    assert response.status_code == 422


# ---------- E4 ----------


@pytest.mark.parametrize(
    ("patient_key", "business_date"),
    [
        pytest.param("P001", "2026-09-01", id="E4-admission-first-day"),
        pytest.param("P002", "2026-09-03", id="E4-readmission-first-day"),
    ],
)
async def test_e4_not_auditable_day_422_without_records(
    api: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    patient_key: str,
    business_date: str,
) -> None:
    """E4／B8：入院首日 → 422「入院首日無前日紀錄可比較」（無逗號）。

    不寫入 audit_runs、audit_findings。
    """
    response = await _post(api, _body(patient_key, business_date))

    assert response.status_code == 422
    _assert_safe_detail(response, FIRST_DAY_DETAIL)
    assert await _count(session_factory, "audit_runs") == 0
    assert await _count(session_factory, "audit_findings") == 0


# ---------- E5 ----------


async def test_e5_no_active_model_409(
    api: AsyncClient,
    fake_llm: FakeLLM,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """E5／B8：沒有使用中的模型設定 → 409，不寫入 audit_findings。

    使用前後日都有護理紀錄的 P001 9/03，確保會呼叫 LLM。
    """
    fake_llm.error = LLMNotConfiguredError()

    response = await _post(api, P001_0903)

    assert response.status_code == 409
    _assert_safe_detail(response, NOT_CONFIGURED_DETAIL)
    assert fake_llm.calls == 1
    assert await _count(session_factory, "audit_findings") == 0
