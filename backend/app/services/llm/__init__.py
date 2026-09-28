"""LLM 相關服務。

LiteLLM 在 import 時預設會從 GitHub 下載模型價格表；醫院內網不可對外連線，
所以在任何子模組 import litellm 之前改用套件內建的價格表。
"""

import os

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
