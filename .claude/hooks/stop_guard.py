#!/usr/bin/env python3
"""Stop 守門：流程還在跑（status=running）時不准主對話結束。

最多擋 3 次，避免卡死；第 3 次之後放行並在 state 記錄 stop_forced。
"""
import json
import os
import sys

root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
path = os.path.join(root, ".flow", "state.json")
if not os.path.exists(path):
    sys.exit(0)

with open(path, encoding="utf-8") as f:
    st = json.load(f)
if st.get("status") != "running":
    sys.exit(0)

st["stop_blocks"] = st.get("stop_blocks", 0) + 1
if st["stop_blocks"] > 3:
    st["stop_forced"] = True
    blocked = False
else:
    blocked = True
with open(path, "w", encoding="utf-8") as f:
    json.dump(st, f, ensure_ascii=False, indent=2)

if blocked:
    sys.stderr.write(
        "流程尚未結束（status=running，第 %s 輪，最後測試=%s）。"
        "請依 /senior-flow 的步驟繼續，最後執行 bash .claude/flow/finish.sh。\n"
        % (st.get("round"), st.get("last_test"))
    )
    sys.exit(2)
sys.exit(0)
