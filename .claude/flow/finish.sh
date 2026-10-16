#!/bin/bash
# 結束流程：檢查 report.md 存在且晚於最後一輪測試，才把 status 改成 done/needs_review
set -u
cd "$(dirname "$0")/../.."
python3 .claude/flow/state.py finish
