"""稽核相關的繁中顯示文字；與 `ward_board.STATUS_LABELS` 相同，集中在 service 層對照。"""

from typing import Final

from app.core.enums import AuditCycle, AuditRunStatus, AvailabilityState, Verdict

AUDIT_RUN_STATUS_LABELS: Final[dict[AuditRunStatus, str]] = {
    AuditRunStatus.COMPLETED: "已完成",
    AuditRunStatus.NOT_APPLICABLE: "當日無此事件",
    AuditRunStatus.DATA_UNAVAILABLE: "院方尚未提供資料",
    AuditRunStatus.FAILED: "執行失敗",
}

AUDIT_CYCLE_LABELS: Final[dict[AuditCycle, str]] = {
    AuditCycle.ONCE_PER_ADMISSION: "一次性",
    AuditCycle.DAILY: "每日",
    AuditCycle.EVENT: "有事件時",
}

# 判定的顯示文字；用詞與病床總覽（`ward_board_status.STATUS_LABELS`）一致
VERDICT_LABELS: Final[dict[Verdict, str]] = {
    Verdict.PASS: "紀錄完整",
    Verdict.WARNING: "需確認",
    Verdict.NEEDS_REVIEW: "無法判定",
    Verdict.ERROR: "缺漏",
}

AVAILABILITY_LABELS: Final[dict[AvailabilityState, str]] = {
    AvailabilityState.AVAILABLE: "可稽核",
    AvailabilityState.NOT_APPLICABLE: "當日無此事件",
    AvailabilityState.DATA_UNAVAILABLE: "院方尚未提供資料",
}
