"""病房與原始資料 API。"""

from httpx import AsyncClient

from tests.hospital_data_samples import P1_KEY, P2_KEY, WARD_CODE


async def test_list_wards(client: AsyncClient) -> None:
    response = await client.get("/api/v1/wards")
    assert response.status_code == 200
    ward = response.json()["wards"][0]
    assert (ward["ward_code"], ward["latest_business_date"], ward["latest_patient_count"]) == (
        WARD_CODE,
        "2026-01-02",
        1,
    )


async def test_bed_board_defaults_to_latest_day_and_is_not_audited(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/wards/{WARD_CODE}/bed-board")
    body = response.json()
    assert response.status_code == 200
    assert (body["business_date"], body["bed_count"], body["pending_bed_count"]) == (
        "2026-01-02",
        1,
        0,
    )
    bed = body["beds"][0]
    assert (bed["bed_code"], bed["status"], bed["summary_text"]) == (
        "W99-001",
        "NOT_AUDITED",
        "尚未稽核",
    )
    assert bed["patient"]["length_of_stay_days"] == 3
    counts = {c["status"]: c["count"] for c in body["status_counts"]}
    assert counts == {"ERROR": 0, "WARNING": 0, "NEEDS_REVIEW": 0, "PASS": 0, "NOT_AUDITED": 1}


async def test_bed_board_for_specific_day(client: AsyncClient) -> None:
    response = await client.get(
        f"/api/v1/wards/{WARD_CODE}/bed-board", params={"business_date": "2026-01-01"}
    )
    assert response.json()["bed_count"] == 2


async def test_bed_board_unknown_date_is_404(client: AsyncClient) -> None:
    response = await client.get(
        f"/api/v1/wards/{WARD_CODE}/bed-board", params={"business_date": "2030-01-01"}
    )
    assert response.status_code == 404


async def test_unknown_ward_is_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/wards/W1/raw-patients")
    assert response.status_code == 404


async def test_raw_patients_include_discharged(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/wards/{WARD_CODE}/raw-patients")
    patients = {p["patient_key"]: p for p in response.json()["patients"]}
    assert patients[P1_KEY]["is_current"] is True
    assert patients[P2_KEY]["is_current"] is False
    assert patients[P1_KEY]["work_checklist_filled_count"] == 2


async def test_patient_detail_counts(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/raw-patients/{P1_KEY}")
    body = response.json()
    counts = {c["category"]: c["count"] for c in body["category_counts"]}
    assert body["business_dates"] == ["2026-01-01", "2026-01-02"]
    assert counts["examination"] == 2
    assert counts["lab_result"] == 2


async def test_timeline_with_category_filter(client: AsyncClient) -> None:
    response = await client.get(
        f"/api/v1/raw-patients/{P1_KEY}/timeline",
        params={"categories": ["vital_sign"], "start_date": "2026-01-01"},
    )
    body = response.json()
    assert body["event_count"] == 1
    assert body["days"][0]["events"][0]["fields"][0] == {"label": "體溫", "value": "36.5℃"}


async def test_timeline_invalid_range_is_422(client: AsyncClient) -> None:
    response = await client.get(
        f"/api/v1/raw-patients/{P1_KEY}/timeline",
        params={"start_date": "2026-01-02", "end_date": "2026-01-01"},
    )
    assert response.status_code == 422


async def test_lab_matrix(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/raw-patients/{P1_KEY}/lab-matrix")
    assert len(response.json()["columns"]) == 2


async def test_source_returns_original_text(client: AsyncClient) -> None:
    response = await client.get(
        f"/api/v1/raw-patients/{P1_KEY}/source", params={"business_date": "2026-01-01"}
    )
    body = response.json()
    assert body["business_date"] == "2026-01-01"
    assert "虛構入院經過" in body["content"]


async def test_unknown_patient_is_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/raw-patients/0000")
    assert response.status_code == 404


async def test_invalid_patient_key_is_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/raw-patients/abc-def")
    assert response.status_code == 422
