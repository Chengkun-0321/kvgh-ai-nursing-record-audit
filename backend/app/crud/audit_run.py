"""`audit_runs` 的查詢與寫入（不 commit，交易邊界在 service）。"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditRun


async def get_latest(
    session: AsyncSession, patient_key: str, rule_code: str, business_date: date
) -> AuditRun | None:
    """某病患某日某規則最新的一次執行（含發現）；從未執行時為 `None`。"""
    stmt = (
        select(AuditRun)
        .where(
            AuditRun.patient_key == patient_key,
            AuditRun.rule_code == rule_code,
            AuditRun.business_date == business_date,
        )
        .order_by(AuditRun.created_at.desc())
        .limit(1)
        .options(selectinload(AuditRun.findings))
    )
    return await session.scalar(stmt)


async def add(session: AsyncSession, run: AuditRun) -> AuditRun:
    """新增一次執行（發現隨 relationship 一併寫入）並 flush 取得預設值。"""
    session.add(run)
    await session.flush()
    return run
