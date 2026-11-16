"""`audit_runs` 的查詢與寫入（不 commit，交易邊界在 service）。"""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
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


async def list_latest_runs(
    session: AsyncSession,
    patient_keys: Sequence[str],
    rule_codes: Sequence[str],
    business_dates: Sequence[date],
) -> list[AuditRun]:
    """多位病患、多項規則、多個稽核日的最新一次執行（含發現），每組（病患、規則、稽核日）只回傳一列。

    一次查詢取回全部，避免病床總覽對每床每規則各查一次。以視窗函式 ROW_NUMBER 在資料庫端
    挑出每組最新一列（SQLite 與 PostgreSQL 皆支援，不使用方言語法）。
    """
    if not (patient_keys and rule_codes and business_dates):
        return []
    group = [AuditRun.patient_key, AuditRun.rule_code, AuditRun.business_date]
    ranked = (
        select(
            AuditRun.id.label("run_id"),
            func.row_number()
            .over(
                partition_by=group,
                order_by=[AuditRun.created_at.desc(), AuditRun.id.desc()],
            )
            .label("rank_in_group"),
        )
        .where(
            AuditRun.patient_key.in_(patient_keys),
            AuditRun.rule_code.in_(rule_codes),
            AuditRun.business_date.in_(business_dates),
        )
        .subquery()
    )
    stmt = (
        select(AuditRun)
        .join(ranked, AuditRun.id == ranked.c.run_id)
        .where(ranked.c.rank_in_group == 1)
        .options(selectinload(AuditRun.findings))
    )
    return list(await session.scalars(stmt))


async def add(session: AsyncSession, run: AuditRun) -> AuditRun:
    """新增一次執行（發現隨 relationship 一併寫入）並 flush 取得預設值。"""
    session.add(run)
    await session.flush()
    return run
