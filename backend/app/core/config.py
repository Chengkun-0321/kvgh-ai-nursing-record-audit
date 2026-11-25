"""應用程式設定：一律經 `get_settings()` 取得，不直接讀 `os.environ`。"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
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
    # 結構化輸出（稽核）格式不符時的重試次數，不含第一次呼叫
    LLM_MAX_RETRIES: int = 2
    # 結構化輸出遇到網路錯誤、429、逾時的重試次數（LiteLLM 指數退避），與格式重試分開計算
    LLM_STRUCTURED_NUM_RETRIES: int = 2
    # 同時進行中的結構化 LLM 呼叫數（一鍵稽核時多張卡片同時送出）
    LLM_MAX_CONCURRENCY: int = 3

    # Demo 登入：固定一組帳密，只來自環境變數；未設定時後端無法啟動（fail closed）
    DEMO_LOGIN_USERNAME: str = Field(min_length=1)
    DEMO_LOGIN_PASSWORD: SecretStr = Field(min_length=1)
    # 登入 session 的有效秒數（預設 12 小時）；cookie 與 token 到期時間共用
    SESSION_MAX_AGE_SECONDS: int = Field(default=43200, gt=0)

    # ChatGPT 訂閱登入的 token 檔目錄；含登入憑證，只能放在不進版控的 data/
    CHATGPT_TOKEN_DIR: Path = DATA_DIR / "chatgpt"
    # 查詢 ChatGPT 帳號可用模型時帶的 Codex 用戶端版本；太舊時新模型不會列出。
    # 有設定時固定使用此版本；未設定時自動查詢 Codex CLI 最新版本，查詢失敗才用 FALLBACK
    CHATGPT_CLIENT_VERSION: str | None = None
    CHATGPT_CLIENT_VERSION_FALLBACK: str = "0.159.2"
    CODEX_LATEST_VERSION_URL: str = "https://registry.npmjs.org/@openai/codex/latest"
    CODEX_VERSION_CACHE_SECONDS: int = 86400

    # 院方提供的每日資料（`<YYYYMMDD>/<病房>/patientlist.json` 與病人檔）；後端只讀不寫
    HOSPITAL_DATA_DIR: Path = PROJECT_ROOT / "data"
    # 首頁與原始資料頁預設顯示的病房
    DEFAULT_WARD_CODE: str = "W63"

    # R02：複製比對回溯天數，含當日（預設當日加前 4 日）
    AUDIT_COPY_LOOKBACK_DAYS: int = 5
    # R06：會診後幾日內要有相應紀錄；暫定值，院方待確認
    AUDIT_CONSULT_FOLLOWUP_DAYS: int = 1


@lru_cache
def get_settings() -> Settings:
    """取得快取的設定物件。"""
    return Settings()
