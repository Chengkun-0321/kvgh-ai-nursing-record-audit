"""Log 設定：只記錄內部代碼與 ID，不記錄病患識別資料、API key 或對話內容。"""

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
# LiteLLM 的 debug log 會輸出完整請求（含 key 與內容），只保留警告以上
_LITELLM_LOGGERS = ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy")


def configure_logging() -> None:
    """設定根 logger 格式，並壓低 LiteLLM 的 log 等級。"""
    logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)
    for name in _LITELLM_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
