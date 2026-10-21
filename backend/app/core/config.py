"""應用程式設定：一律經 `get_settings()` 取得，不直接讀 `os.environ`。"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
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
    # 查詢 ChatGPT 帳號可用模型時帶的 Codex 用戶端版本；太舊時新模型不會列出。
    # 有設定時固定使用此版本；未設定時自動查詢 Codex CLI 最新版本，查詢失敗才用 FALLBACK
    CHATGPT_CLIENT_VERSION: str | None = None
    CHATGPT_CLIENT_VERSION_FALLBACK: str = "0.159.2"
    CODEX_LATEST_VERSION_URL: str = "https://registry.npmjs.org/@openai/codex/latest"
    CODEX_VERSION_CACHE_SECONDS: int = 86400

    # 稽核格式重試：LLM 輸出不符 schema 時附上驗證錯誤再問，最多重試這麼多次（總呼叫 1 + 此值）。
    # 環境變數 LLM_MAX_RETRIES，預設 2（待補進 .env.example）
    LLM_MAX_RETRIES: int = 2

    # 院方每日資料包根目錄（`<YYYYMMDD>/manifest.json`＋病患檔），只讀不寫。
    # 環境變數 MOCK_DATA_DIR，預設為專案根目錄的 mock_data/（待補進 .env.example）
    MOCK_DATA_DIR: Path = PROJECT_ROOT / "mock_data"
    # 匯入時原封保存原始檔的目錄（`<YYYY-MM-DD>/<檔名>`），不進版控。
    # 環境變數 RAW_DATA_DIR，預設 backend/data/raw/（待補進 .env.example）
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    # R02 比對範圍：當日之外，再往前取幾個「有資料包」的業務日。
    # 環境變數 R02_LOOKBACK_DAYS，預設 2（待補進 .env.example）
    R02_LOOKBACK_DAYS: int = 2


@lru_cache
def get_settings() -> Settings:
    """取得快取的設定物件。"""
    return Settings()
