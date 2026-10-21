"""models 與 schemas 共用的欄位長度與數量上限，以及業務時區。"""

from datetime import timedelta, timezone

# 業務日期與畫面時間一律以 Asia/Taipei 計算；台灣無日光節約時間，以固定 +08:00 表示，
# 不依賴執行環境是否安裝時區資料庫
BUSINESS_TIMEZONE = timezone(timedelta(hours=8), "Asia/Taipei")

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

# 病患匿名鍵（目前等於院方 patient_id）
PATIENT_KEY_MAX_LENGTH = 64
