"""R02 測試共用工具（資料包內容完全虛構）。

- 複製資料包、修改副本
- 假的 StructuredLLM
- 解析渲染後的 prompt、查詢資料表筆數

本檔不是測試檔，由各測試以 importlib 依路徑載入。
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, literal_column, select, table, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.schemas.llm_structured import LLMRequest, LLMResult
from app.services.audit.rules.r02_copy_paste import R02LLMOutput
from app.services.audit.runner import run_patient_audit
from app.services.ingestion.sources import LocalFixtureSource
from app.services.llm.prompt_loader import render_prompt

JsonDict = dict[str, Any]

FIXTURE_ROOT = Path(__file__).resolve().parent
FORBIDDEN_WORDS = ("寫錯", "抄襲", "違規", "沒有寫")
RECORD_TABLES = (
    "admissions",
    "nursing_progress_notes",
    "vital_signs",
    "lab_results",
    "tubes",
)
ALL_TABLES = (
    "ingestion_batches",
    "ingestion_errors",
    *RECORD_TABLES,
    "audit_runs",
    "audit_findings",
)

# 護理過程紀錄 content 中的原文片段，可作為有效 Evidence
P001_0903_EXCERPT = "主訴傷口疼痛分數三分"
P001_0905_01_EXCERPT = "病人下床活動情形穩定"
P001_0905_02_EXCERPT = "家屬陪伴在側"

DEFAULT_OUTPUT: JsonDict = {"verdict": "PASS", "notes": [], "evidence": []}

_DATE_ATTR = re.compile(r'date="(\d{4}-\d{2}-\d{2})"')
_RECORD_TAG = re.compile(r'<record source="([^"]+)" id="([^"]+)" date="(\d{4}-\d{2}-\d{2})"')


def copy_packages(tmp_path: Path) -> Path:
    """把虛構資料包複製到 tmp_path / "mock"，測試只修改副本。"""
    destination = tmp_path / "mock"
    shutil.copytree(
        FIXTURE_ROOT,
        destination,
        ignore=shutil.ignore_patterns("*.py", "__pycache__"),
    )
    return destination


def prepare_data_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """複製資料包，設定 MOCK_DATA_DIR、RAW_DATA_DIR 後清除設定快取。"""
    root = copy_packages(tmp_path)
    monkeypatch.setenv("MOCK_DATA_DIR", str(root))
    monkeypatch.setenv("RAW_DATA_DIR", str(tmp_path / "raw"))
    get_settings.cache_clear()
    return root


def read_json(path: Path) -> JsonDict:
    data: JsonDict = json.loads(path.read_text(encoding="utf-8"))
    return data


def write_json(path: Path, data: JsonDict) -> None:
    content = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(content, encoding="utf-8")


def patient_file(root: Path, day: str, patient_id: str) -> Path:
    """day 為資料夾名稱 YYYYMMDD。"""
    return root / day / f"{patient_id}.json"


def edit_json(path: Path, editor: Callable[[JsonDict], None]) -> None:
    data = read_json(path)
    editor(data)
    write_json(path, data)


def set_notes(root: Path, day: str, patient_id: str, notes: list[JsonDict]) -> None:
    """把某日某病患檔的護理過程紀錄換成 notes。"""

    def _editor(data: JsonDict) -> None:
        data["nursing_progress_notes"] = notes

    edit_json(patient_file(root, day, patient_id), _editor)


def all_note_contents(root: Path = FIXTURE_ROOT) -> list[str]:
    """資料包中所有護理過程紀錄的 content。"""
    contents: list[str] = []
    for path in sorted(root.glob("*/P*.json")):
        notes = read_json(path)["nursing_progress_notes"]
        contents.extend(str(item["content"]) for item in notes)
    return contents


def snapshot(root: Path) -> dict[str, tuple[str, int] | None]:
    """目錄快照：相對路徑 → (sha256, st_mtime_ns)；目錄為 None。"""
    result: dict[str, tuple[str, int] | None] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            result[relative] = None
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result[relative] = (digest, path.stat().st_mtime_ns)
    return result


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def note(
    record_id: str,
    *,
    similar_record_id: str | None = None,
    similarity_percent: float | None = None,
    issue_types: Iterable[str] = (),
    referenced_record_id: str | None = None,
) -> JsonDict:
    """組一筆 LLM 回傳的 R02 逐筆判斷（必填欄位一律明確給值）。"""
    return {
        "record_id": record_id,
        "similar_record_id": similar_record_id,
        "similarity_percent": similarity_percent,
        "issue_types": list(issue_types),
        "referenced_record_id": referenced_record_id,
    }


def evidence(record_id: str, excerpt: str) -> JsonDict:
    return {"record_id": record_id, "field": "content", "excerpt": excerpt}


def llm_output(
    verdict: str,
    notes: Iterable[JsonDict] = (),
    evidences: Iterable[JsonDict] = (),
) -> JsonDict:
    return {"verdict": verdict, "notes": list(notes), "evidence": list(evidences)}


class FakeStructuredLLM:
    """假的 StructuredLLM。

    記錄每次收到的 request 與 output_schema；
    回傳預設的 LLMResult，或拋出指定例外。
    """

    def __init__(
        self,
        *,
        output: JsonDict | None = None,
        error: BaseException | None = None,
        system_prompt_version: int | None = 7,
    ) -> None:
        self.output = output
        self.error = error
        self.system_prompt_version = system_prompt_version
        self.requests: list[LLMRequest] = []
        self.schemas: list[type] = []

    @property
    def calls(self) -> int:
        return len(self.requests)

    async def __call__(self, request: LLMRequest, output_schema: type) -> LLMResult:
        self.requests.append(request)
        self.schemas.append(output_schema)
        if self.error is not None:
            raise self.error
        payload = self.output if self.output is not None else DEFAULT_OUTPUT
        return LLMResult(
            parsed=R02LLMOutput.model_validate(payload),
            model="fake-model",
            prompt_version=f"{request.prompt_name}/{request.prompt_version}",
            system_prompt_version=self.system_prompt_version,
        )


async def run_r02(
    session: AsyncSession,
    root: Path,
    llm: FakeStructuredLLM,
    *,
    patient_key: str,
    business_date: date,
) -> JsonDict:
    """以關鍵字參數呼叫 run_patient_audit，回傳 model_dump(mode="json")。"""
    finding = await run_patient_audit(
        session=session,
        source=LocalFixtureSource(root),
        llm=llm,
        patient_key=patient_key,
        business_date=business_date,
        rule_code="R02",
    )
    dumped: JsonDict = finding.model_dump(mode="json")
    return dumped


async def count_rows(session: AsyncSession, table_name: str) -> int:
    query = select(func.count()).select_from(table(table_name))
    result = await session.execute(query)
    return int(result.scalar_one())


async def count_all(session: AsyncSession, tables: Iterable[str] = ALL_TABLES) -> dict[str, int]:
    return {name: await count_rows(session, name) for name in tables}


async def table_cells(session: AsyncSession, table_name: str) -> list[str]:
    """把整張表每格轉成字串，用來檢查內容而不依賴欄位名稱。"""
    query = select(literal_column("*")).select_from(table(table_name))
    rows = (await session.execute(query)).all()
    return [str(value) for row in rows for value in row]


async def batch_dates(session: AsyncSession) -> list[str]:
    query = text("SELECT business_date FROM ingestion_batches")
    rows = (await session.execute(query)).all()
    return [str(row[0])[:10] for row in rows]


def render(request: LLMRequest) -> str:
    """BR5：以 prompt_loader 渲染 request，取得送給 LLM 的規則 prompt。"""
    return render_prompt(request.prompt_name, request.prompt_version, request.variables)


def prompt_dates(prompt: str) -> set[str]:
    return set(_DATE_ATTR.findall(prompt))


def record_tags(prompt: str) -> list[tuple[str, str, str]]:
    """回傳 prompt 中每個 record 標籤的 (source, id, date)。"""
    return _RECORD_TAG.findall(prompt)


def record_ids(prompt: str) -> set[str]:
    return {record_id for _, record_id, _ in record_tags(prompt)}


def day_blocks(prompt: str, tag: str) -> dict[str, str]:
    """回傳 {日期: 區塊內容}，tag 為 current_day 或 previous_day。"""
    pattern = re.compile(
        rf'<{tag} date="(\d{{4}}-\d{{2}}-\d{{2}})"[^>]*>(.*?)</{tag}>',
        re.DOTALL,
    )
    return dict(pattern.findall(prompt))


def assert_no_forbidden_words(message: str) -> None:
    """BR9／A5：訊息不得包含禁止用語。"""
    for word in FORBIDDEN_WORDS:
        assert word not in message, f"訊息含禁止用語「{word}」：{message}"
