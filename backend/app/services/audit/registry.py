"""規則註冊表：新增第 8 項＝新增規則模組＋prompt 目錄＋這裡一行。"""

from typing import Final

from app.services.audit.rules.base import AuditRule
from app.services.audit.rules.r01_admission_course import R01AdmissionCourse
from app.services.audit.rules.r02_copy_paste import R02CopyPaste
from app.services.audit.rules.r03_admission_completeness import R03AdmissionCompleteness
from app.services.audit.rules.r04_assessment_followup import R04AssessmentFollowup
from app.services.audit.rules.r05_transfer_summary import R05TransferSummary
from app.services.audit.rules.r06_consultation import R06Consultation
from app.services.audit.rules.r07_medication_followup import R07MedicationFollowup

# 依規則代碼排序，畫面依此順序顯示
RULE_REGISTRY: Final[dict[str, AuditRule]] = {
    rule.code: rule
    for rule in (
        R01AdmissionCourse(),
        R02CopyPaste(),
        R03AdmissionCompleteness(),
        R04AssessmentFollowup(),
        R05TransferSummary(),
        R06Consultation(),
        R07MedicationFollowup(),
    )
}
