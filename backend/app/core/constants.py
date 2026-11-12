"""models、schemas 與 services 共用的常數（欄位長度、數量上限、時區）。"""

LLM_CONFIG_NAME_MAX_LENGTH = 100
LLM_MODEL_MAX_LENGTH = 200
LLM_API_BASE_MAX_LENGTH = 500
LLM_API_KEY_MAX_LENGTH = 1000
LLM_API_KEY_HINT_MAX_LENGTH = 32
LLM_TIMEOUT_MIN_SECONDS = 5
LLM_TIMEOUT_MAX_SECONDS = 600

# 測試對話：歷史只存在前端，每次送出完整訊息；上限避免一次送出過大的請求
CHAT_MAX_MESSAGES = 40
CHAT_MAX_MESSAGE_CHARS = 8000

# 共用 system prompt：每次呼叫都會送出，上限避免占用過多 token
LLM_SYSTEM_PROMPT_MAX_CHARS = 8000

SETTING_TARGET_MAX_LENGTH = 64
SETTING_ACTOR_MAX_LENGTH = 100

# 病房代碼（如 W63）：API 路徑參數與讀取院方資料夾共用同一規則
WARD_CODE_PATTERN = r"^[A-Z]{1,3}\d{1,4}$"

# 院方資料的時間沒有時區，一律視為台北時間
BUSINESS_TIMEZONE = "Asia/Taipei"
