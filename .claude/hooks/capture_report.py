#!/usr/bin/env python3
"""SubagentStop：把 consistency-checker 的最後回覆原樣存成 .flow/report.md。

Claude Code 不讓 subagent 自己寫報告檔，所以由腳本存檔，不經過指揮轉手。
每次觸發都把輸入欄位名稱記到 .flow/hook_debug.jsonl，方便核對。
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

if agent_type == "consistency-checker" and msg.strip():
    with open(os.path.join(flow, "report.md"), "w", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")
sys.exit(0)
