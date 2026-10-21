#!/usr/bin/env python3
"""SubagentStop：把 consistency-checker 的最後回覆原樣存成 .flow/report.md。

Claude Code 不讓 subagent 自己寫報告檔，所以由腳本存檔，不經過指揮轉手。
每次觸發都把輸入欄位名稱記到 .flow/hook_debug.jsonl，方便核對。
流程執行中另由 .claude/flow/record.py 把該節點的輸入、過程、輸出存到 flow-records/。
"""
import json
import os
import sys
import time

data = json.load(sys.stdin)
root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
flow = os.path.join(root, ".flow")
os.makedirs(flow, exist_ok=True)

agent_type = data.get("agent_type")
msg = data.get("last_assistant_message") or ""
with open(os.path.join(flow, "hook_debug.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps({"ts": time.strftime("%H:%M:%S"), "event": data.get("hook_event_name"),
                        "agent_type": agent_type, "keys": sorted(data.keys()),
                        "msg_chars": len(msg)}, ensure_ascii=False) + "\n")

# subagent 以交回工具回報時 last_assistant_message 為空，改從 transcript 取交回內容
try:
    sys.path.insert(0, os.path.join(root, ".claude", "flow"))
    import record
except Exception:  # noqa: BLE001
    record = None
if not msg.strip() and record is not None:
    msg = record.final_output(data, record.read_transcript(data.get("agent_transcript_path")))

if agent_type == "consistency-checker" and msg.strip():
    with open(os.path.join(flow, "report.md"), "w", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")

# 節點紀錄失敗不影響流程本身
try:
    record.record_subagent(data)
except Exception as e:  # noqa: BLE001
    with open(os.path.join(flow, "hook_debug.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%H:%M:%S"), "record_error": repr(e)}, ensure_ascii=False) + "\n")
sys.exit(0)
