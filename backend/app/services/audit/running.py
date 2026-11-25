"""程序內的「稽核中」登記：記錄哪些稽核正在這個後端行程裡執行。

稽核在處理請求的同一個行程內執行；瀏覽器中止請求（重新整理、切換日期）後，
後端仍會跑完並寫入結果。登記放在記憶體，與稽核本身同生共死：行程結束時兩者一起消失，
不會留下卡住的「稽核中」。

限制：多個後端行程（多 worker、多台主機）之間看不到彼此的登記，與 LLM 併發閘門相同。
屆時改存資料庫，介面（`is_running`／`hold`）不變（見 ADR 0011）。
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Final

from app.core.exceptions import AuditAlreadyRunningError

ALREADY_RUNNING_MESSAGE: Final = "此項目正在稽核中，請稍候"


@dataclass(frozen=True)
class RunningKey:
    """一項稽核的識別：病人、規則、規則的稽核日（入院規則為入院日）。"""

    patient_key: str
    rule_code: str
    business_date: date


class RunningAudits:
    """執行中的稽核登記。

    只在單一 event loop 內使用：檢查與登記之間沒有 `await`，不會有兩個請求同時通過檢查。
    """

    def __init__(self) -> None:
        self._keys: set[RunningKey] = set()

    def is_running(self, key: RunningKey) -> bool:
        """這項稽核是否正在執行。"""
        return key in self._keys

    @contextmanager
    def hold(self, key: RunningKey) -> Iterator[None]:
        """執行期間登記為稽核中，結束（成功、失敗或例外）時除名。

        Raises:
            AuditAlreadyRunningError: 同一項已在執行中（不重複呼叫模型）。
        """
        if key in self._keys:
            raise AuditAlreadyRunningError(ALREADY_RUNNING_MESSAGE)
        self._keys.add(key)
        try:
            yield
        finally:
            self._keys.discard(key)


# 整個後端行程共用一份；AuditService 每個請求建立一次，因此不能放在 service 實例上
RUNNING_AUDITS: Final = RunningAudits()
