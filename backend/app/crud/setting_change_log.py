"""`setting_change_logs` 的寫入（不 commit）。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting_change_log import SettingChangeLog


async def add(session: AsyncSession, log: SettingChangeLog) -> None:
    """新增一筆設定變更紀錄。"""
    session.add(log)
    await session.flush()
