"""稽核規則登錄表：runner 只依代碼從這裡取得規則類別（Strategy），新增規則不需修改 runner。"""

from typing import Final

from app.services.audit.base import AuditRule
from app.services.audit.rules.r02_copy_paste import R02CopyPasteRule

RULE_REGISTRY: Final[dict[str, type[AuditRule]]] = {
    R02CopyPasteRule.code: R02CopyPasteRule,
}
