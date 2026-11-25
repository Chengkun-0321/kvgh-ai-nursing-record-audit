"""稽核的輸出結構：Evidence（程式回填後的完整版）、執行結果、每日總覽。

所有顯示文字（狀態名稱、可否執行、日期清單）由後端算好回傳，前端只渲染（見 ADR 0009）。
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import AuditCycle, AuditRunStatus, AvailabilityState, Verdict


class Evidence(BaseModel):
    """判定依據：excerpt 已確認存在於 record_id 的原文中。"""

    source: str
    # 來源的繁中名稱與院方原始時間字串，供畫面直接顯示
    source_label: str
    record_id: str
    field: str | None
    business_date: date
    time_text: str
    recorded_at: datetime | None
    excerpt: str


class AuditFindingRead(BaseModel):
    """一次執行中的一個發現。"""

    model_config = ConfigDict(from_attributes=True)

    position: int
    item: str
    verdict: Verdict
    verdict_label: str
    message: str
    evidence: list[Evidence]


class AuditRunRead(BaseModel):
    """一次稽核執行的結果；`status_label` 為畫面顯示用的狀態文字。"""

    id: UUID
    rule_code: str
    rule_name: str
    patient_key: str
    business_date: date
    status: AuditRunStatus
    status_label: str
    status_reason: str | None
    verdict: Verdict | None
    verdict_label: str | None
    summary: str | None
    findings: list[AuditFindingRead]
    details: dict[str, Any] | None
    model: str | None
    prompt_version: int | None
    system_prompt_version: int | None
    duration_ms: int | None
    created_at: datetime


class AvailabilityRead(BaseModel):
    """規則在該日是否可執行，以及不可執行的原因（繁中）。"""

    state: AvailabilityState
    label: str
    reason: str | None


class AuditRuleStatusRead(BaseModel):
    """每日總覽中的一項規則。"""

    rule_code: str
    name: str
    description: str
    cycle: AuditCycle
    cycle_label: str
    effective_business_date: date
    availability: AvailabilityRead
    can_run: bool
    # 一鍵稽核是否包含此項：可執行、不在稽核中，且入院規則尚未有已完成的結果
    include_in_run_all: bool
    # 這項稽核是否正在後端執行中（重新整理或切換日期後，畫面據此繼續顯示稽核中）
    is_running: bool
    latest_run: AuditRunRead | None


class PatientAuditDayRead(BaseModel):
    """病患某日的稽核總覽。"""

    patient_key: str
    ward_code: str
    bed_code: str
    admitted_at: datetime | None
    admitted_at_text: str | None
    business_date: date
    available_dates: list[date]
    previous_date: date | None
    next_date: date | None
    rules: list[AuditRuleStatusRead]
