"""`llm_system_prompts` 的查詢與寫入（不 commit，交易邊界在 service）。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_system_prompt import LlmSystemPrompt


async def get_latest(session: AsyncSession) -> LlmSystemPrompt | None:
    """取得版本號最大的一筆（目前使用的版本）。"""
    return await session.scalar(
        select(LlmSystemPrompt).order_by(LlmSystemPrompt.version.desc()).limit(1)
    )


async def add(session: AsyncSession, prompt: LlmSystemPrompt) -> LlmSystemPrompt:
    """新增一個版本並 flush 取得預設值。"""
    session.add(prompt)
    await session.flush()
    return prompt
