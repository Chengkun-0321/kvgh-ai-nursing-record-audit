"""ChatGPT 裝置碼登入的輪詢執行緒：專屬 daemon 執行緒、有名額上限（不 import litellm）。

輪詢最長約 15 分鐘且無法中止，登出後被放棄的輪詢仍會跑到逾時；以名額限制同時存在的執行緒數，
反覆登入登出也不會無限累積。名額（semaphore）由呼叫端保存，本模組不持有狀態。
"""

import asyncio
import concurrent.futures
import threading
from collections.abc import Callable
from typing import Final

from app.core.exceptions import ChatgptLoginError

# 進行中的登入只有一個，另留 2 個名額給被放棄的輪詢
LOGIN_THREAD_LIMIT: Final = 3
LOGIN_THREAD_NAME: Final = "chatgpt-login-poll"
_TOO_MANY_LOGINS_MESSAGE: Final = "登入嘗試過於頻繁，請等候約 15 分鐘後再重新登入"


def create_login_thread_slots() -> threading.BoundedSemaphore:
    """建立輪詢執行緒名額；執行緒結束才歸還，取消等待中的 task 不會提早歸還。"""
    return threading.BoundedSemaphore(LOGIN_THREAD_LIMIT)


def start_login_thread[T](
    work: Callable[[], T], slots: threading.BoundedSemaphore
) -> asyncio.Future[T]:
    """在專屬、有名額上限的 daemon 執行緒執行登入輪詢，回傳可 await 的結果。

    不用 `asyncio.to_thread`：輪詢會長時間占住院方資料讀檔共用的預設執行緒池。
    不用 `ThreadPoolExecutor`：程式結束時會 join 工作執行緒，關閉應用程式會卡到輪詢逾時；
    這裡的執行緒只做 HTTP 輪詢與換發、不寫檔，程式結束時直接中止不會留下半寫的 token 檔。

    Args:
        work: 在執行緒中執行的輪詢與換發。
        slots: 名額（`create_login_thread_slots()` 建立）；執行緒結束時歸還。

    Returns:
        `work` 的結果；`work` 拋出的例外會在 await 時拋出。

    Raises:
        ChatgptLoginError: 名額已滿。
    """
    if not slots.acquire(blocking=False):
        raise ChatgptLoginError(_TOO_MANY_LOGINS_MESSAGE)
    result: concurrent.futures.Future[T] = concurrent.futures.Future()

    def run() -> None:
        try:
            if result.set_running_or_notify_cancel():
                result.set_result(work())
        except BaseException as exc:
            # 交給等待中的 task 處理；留在執行緒內會讓 task 永遠等不到結果
            result.set_exception(exc)
        finally:
            slots.release()

    try:
        threading.Thread(target=run, name=LOGIN_THREAD_NAME, daemon=True).start()
    except RuntimeError:
        slots.release()
        raise
    return asyncio.wrap_future(result)
