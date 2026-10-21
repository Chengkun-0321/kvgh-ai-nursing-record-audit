"""R02 訊息模板測試：BR9（含禁止用語檢查，輔助 A5、A11 的輸出面）。"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from r02_support import (
    FORBIDDEN_WORDS,
    P001_0903_EXCERPT,
    P001_0905_01_EXCERPT,
    P001_0905_02_EXCERPT,
    FakeStructuredLLM,
    assert_no_forbidden_words,
    evidence,
    llm_output,
    note,
    run_r02,
)
from sqlalchemy.ext.asyncio import AsyncSession

SEP_03 = date(2026, 9, 3)
NOTE_0903 = "NPN-P001-0903-01"
NOTE_0902 = "NPN-P001-0902-01"
VALID_EVIDENCE = evidence(NOTE_0903, P001_0903_EXCERPT)

SIMILAR_SEGMENT = "今日 09:30 紀錄（NPN-P001-0903-01）與 9/02 紀錄（NPN-P001-0902-01）相似 98.0%"
CLINICAL_CHANGED_SUFFIX = "，但生命徵象／檢驗／管路已有變化，請確認是否需更新"
OUTDATED_MESSAGE = "今日 09:30 紀錄（NPN-P001-0903-01）引用 9/02 的資料作為今日狀況，請確認"
NO_ISSUE_MESSAGE = "未見與前日紀錄複製或引用非當日資料的情形"
MULTI_FIRST = "今日 09:30 紀錄（NPN-P001-0905-01）與 9/03 紀錄（NPN-P001-0903-01）相似 95.0%"
MULTI_SECOND = "今日 15:00 紀錄（NPN-P001-0905-02）與 9/02 紀錄（NPN-P001-0902-01）相似 90.0%"


async def _message_for(
    session: AsyncSession, root: Path, output: dict[str, Any], day: date = SEP_03
) -> str:
    llm = FakeStructuredLLM(output=output)
    result = await run_r02(session, root, llm, patient_key="P001", business_date=day)
    message: str = result["message"]
    assert_no_forbidden_words(message)
    return message


@pytest.mark.parametrize("issue", ["copy", "unchanged"])
async def test_br9_copy_or_unchanged_message(
    session: AsyncSession, data_root: Path, issue: str
) -> None:
    """BR9：copy／unchanged 套「今日 HH:MM 紀錄…相似 x%」模板，結尾「，請確認」。

    百分比以 98 輸入，輸出為 98.0。
    """
    notes = [
        note(NOTE_0903, similar_record_id=NOTE_0902, similarity_percent=98, issue_types=[issue])
    ]
    output = llm_output("WARNING", notes=notes, evidences=[VALID_EVIDENCE])

    message = await _message_for(session, data_root, output)

    assert message == SIMILAR_SEGMENT + "，請確認"


async def test_br9_copy_with_clinical_changed_message(
    session: AsyncSession, data_root: Path
) -> None:
    """BR9：copy＋clinical_changed → 在前段後面加上臨床資料已變化的提醒。"""
    notes = [
        note(
            NOTE_0903,
            similar_record_id=NOTE_0902,
            similarity_percent=98,
            issue_types=["copy", "clinical_changed"],
        )
    ]
    output = llm_output("WARNING", notes=notes, evidences=[VALID_EVIDENCE])

    message = await _message_for(session, data_root, output)

    assert message == SIMILAR_SEGMENT + CLINICAL_CHANGED_SUFFIX + "，請確認"


async def test_br9_outdated_reference_message(session: AsyncSession, data_root: Path) -> None:
    """BR9：outdated_reference 引用 9/02 的生命徵象。

    訊息為「今日 09:30 紀錄（…）引用 9/02 的資料作為今日狀況，請確認」。
    """
    notes = [
        note(
            NOTE_0903,
            issue_types=["outdated_reference"],
            referenced_record_id="VS-P001-0902-1",
        )
    ]
    output = llm_output("WARNING", notes=notes, evidences=[VALID_EVIDENCE])

    message = await _message_for(session, data_root, output)

    assert message == OUTDATED_MESSAGE


async def test_br9_pass_message(session: AsyncSession, data_root: Path) -> None:
    """BR9：PASS 的訊息恰好為固定模板。"""
    llm_note = note(NOTE_0903, similar_record_id=NOTE_0902, similarity_percent=20)
    output = llm_output("PASS", notes=[llm_note])

    message = await _message_for(session, data_root, output)

    assert message == NO_ISSUE_MESSAGE


async def test_br9_multiple_issues_joined_with_fullwidth_semicolon(
    session: AsyncSession, data_root: Path
) -> None:
    """BR9：9/05 兩筆當日紀錄各有問題 → 以「；」串接，結尾「，請確認」。"""
    notes = [
        note(
            "NPN-P001-0905-01",
            similar_record_id="NPN-P001-0903-01",
            similarity_percent=95,
            issue_types=["copy"],
        ),
        note(
            "NPN-P001-0905-02",
            similar_record_id=NOTE_0902,
            similarity_percent=90,
            issue_types=["unchanged"],
        ),
    ]
    evidences = [
        evidence("NPN-P001-0905-01", P001_0905_01_EXCERPT),
        evidence("NPN-P001-0905-02", P001_0905_02_EXCERPT),
    ]
    output = llm_output("WARNING", notes=notes, evidences=evidences)

    message = await _message_for(session, data_root, output, date(2026, 9, 5))

    assert "；" in message
    assert message.endswith("，請確認")
    assert MULTI_FIRST in message
    assert MULTI_SECOND in message


@pytest.mark.parametrize(
    "output",
    [
        pytest.param(llm_output("WARNING"), id="BR9-warning-no-evidence"),
        pytest.param(
            llm_output(
                "WARNING",
                [
                    note(
                        NOTE_0903,
                        similar_record_id=NOTE_0902,
                        similarity_percent=99,
                        issue_types=["copy", "clinical_changed"],
                    )
                ],
                [VALID_EVIDENCE],
            ),
            id="BR9-warning-clinical-changed",
        ),
        pytest.param(llm_output("PASS"), id="BR9-pass"),
    ],
)
async def test_br9_messages_have_no_forbidden_words(
    session: AsyncSession, data_root: Path, output: dict[str, Any]
) -> None:
    """BR9／A5：各情境產生的 message 都不含「寫錯」「抄襲」「違規」「沒有寫」。"""
    message = await _message_for(session, data_root, output)

    assert message


def test_br9_rule_source_has_no_forbidden_words() -> None:
    """BR9／A5：r02_copy_paste.py 原始碼不含禁止用語。"""
    rules_dir = Path(__file__).resolve().parents[3] / "app" / "services" / "audit"
    source_path = rules_dir / "rules" / "r02_copy_paste.py"

    source = source_path.read_text(encoding="utf-8")

    for word in FORBIDDEN_WORDS:
        assert word not in source, f"r02_copy_paste.py 含禁止用語「{word}」"
