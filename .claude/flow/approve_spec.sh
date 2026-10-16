#!/bin/bash
# 人確認 spec：只能由人在終端機執行（或在 Claude Code 輸入 `! bash .claude/flow/approve_spec.sh`）。
# guard 不允許 AI 執行這支腳本，也不允許 AI 寫入確認紀錄。
set -eu
cd "$(dirname "$0")/../.."
python3 .claude/flow/state.py approve
