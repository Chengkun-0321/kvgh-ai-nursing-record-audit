"""`audit_runs`、`audit_findings` 的查詢與寫入（不 commit，交易邊界在 service）。"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditFinding, AuditRun


async def add_run(session: AsyncSession, run: AuditRun) -> AuditRun:
    """新增稽核批次並 flush 取得 ID。"""
    session.add(run)
    await session.flush()
    return run


async def add_finding(session: AsyncSession, finding: AuditFinding) -> AuditFinding:
    """新增稽核結果並 flush 取得預設值。"""
    session.add(finding)
    await session.flush()
    return finding


async def list_findings_newest_first(
    session: AsyncSession, patient_key: str
) -> Sequence[AuditFinding]:
    """該病患所有稽核結果，由新到舊。

    `audited_at` 相同時，再依稽核批次開始時間與建立時間排序，確保連續兩次稽核取到後者。
    """
    result = await session.scalars(
        select(AuditFinding)
        .join(AuditRun, AuditRun.id == AuditFinding.audit_run_id)
        .where(AuditFinding.patient_key == patient_key)
        .order_by(
            AuditFinding.audited_at.desc(),
            AuditRun.started_at.desc(),
            AuditFinding.created_at.desc(),
        )
    )
    return result.all()
