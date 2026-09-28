"""應用程式設定：一律經 `get_settings()` 取得，不直接讀 `os.environ`。"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_ROOT / "data"


class Settings(BaseSettings):
    """後端設定，來源為環境變數與 `backend/.env`（新增欄位時同步更新 `.env.example`）。"""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 開發用 SQLite 放在 backend/data/（不進版控）；正式環境改為 PostgreSQL 連線字串
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR / 'app.db'}"
    DATA_DIR: Path = DATA_DIR
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # LLM API key 以 Fernet 加密存 DB，金鑰只來自環境變數
    LLM_KEY_ENCRYPTION_KEY: SecretStr
    LLM_DEFAULT_TIMEOUT_SECONDS: int = 60
    # 測試對話要立即呈現錯誤，預設不重試
    LLM_CHAT_NUM_RETRIES: int = 0

    # ChatGPT 訂閱登入的 token 檔目錄；含登入憑證，只能放在不進版控的 data/
    CHATGPT_TOKEN_DIR: Path = DATA_DIR / "chatgpt"
    # 查詢 ChatGPT 帳號可用模型時帶的 Codex 用戶端版本；太舊時新模型可能不會列出
    CHATGPT_CLIENT_VERSION: str = "0.157.1"


@lru_cache
def get_settings() -> Settings:
    """取得快取的設定物件。"""
    return Settings()
