"""稽核規則的共同介面。

規則是純函式：不碰 DB、不呼叫 LLM、無副作用。所需資料由 `AuditContext` 提供，
執行流程（寫入、LLM 呼叫、Evidence 核對）由 `service.py` 統一處理。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import ClassVar, Protocol, runtime_checkable

from app.core.enums import AuditCycle, AvailabilityState
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceRecord


@dataclass(frozen=True)
class Availability:
    """規則在某日是否可執行；不可執行時 `reason` 說明原因（繁中）。"""

    state: AvailabilityState
    reason: str | None = None


def available() -> Availability:
    """可執行。"""
    return Availability(AvailabilityState.AVAILABLE)


def not_applicable(reason: str) -> Availability:
    """當日不適用，例如當日沒有會診。"""
    return Availability(AvailabilityState.NOT_APPLICABLE, reason)


def data_unavailable(reason: str) -> Availability:
    """院方未提供所需資料，或規則尚未實作。"""
    return Availability(AvailabilityState.DATA_UNAVAILABLE, reason)


@dataclass(frozen=True)
class AuditInput:
    """送給 LLM 的資料。

    `variables` 是 prompt 模板的字串變數；`records` 是本次可被引用的紀錄
    （Evidence 只能指向這裡的 record_id）。`records_block` 由 service 依 `records` 渲染。
    `facts` 是程式算出、要隨結果一起保存的資料（例如相似度參考值），會併入結果的 details。
    """

    variables: Mapping[str, str]
    records: tuple[SourceRecord, ...] = ()
    facts: Mapping[str, object] = field(default_factory=dict)


class AuditRule(Protocol):
    """稽核規則介面；新增規則＝新增模組＋prompt 目錄＋註冊一行。"""

    code: ClassVar[str]
    name: ClassVar[str]
    short_name: ClassVar[str]
    description: ClassVar[str]
    cycle: ClassVar[AuditCycle]
    prompt_name: ClassVar[str]
    prompt_version: ClassVar[int]
    output_schema: ClassVar[type[RuleOutput]]

    def check_availability(self, ctx: AuditContext) -> Availability:
        """判斷規則在 `ctx.business_date` 是否可執行。"""
        ...

    def build_input(self, ctx: AuditContext) -> AuditInput:
        """整理送給 LLM 的資料；只在 `check_availability` 為可執行時呼叫。"""
        ...

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        """規則專屬的輸出驗證；不符時拋出 `LLMOutputError`，結果轉為 NEEDS_REVIEW。"""
        ...


@runtime_checkable
class LabelsFindings(Protocol):
    """選用介面：規則要替某些發現指定專屬顯示文字時實作。"""

    def finding_labels(self, details: Mapping[str, object] | None) -> Mapping[str, str]:
        """回傳「發現項目名稱 → 顯示文字」；只取代「紀錄完整」與「無法判定」的預設文字。"""
        ...
