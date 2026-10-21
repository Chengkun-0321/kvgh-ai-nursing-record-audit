#!/bin/bash
# 開始新的一次流程：清掉上一次的過程紀錄（程式與測試目錄不清，由角色覆寫）
set -eu
cd "$(dirname "$0")/../.."
# spec 必須經人確認、且確認後未被修改，否則不開始
python3 .claude/flow/state.py check_spec
# 角色讀寫範圍不得破壞 coder／test-designer 的隔離
python3 .claude/flow/state.py check_config
rm -rf .flow
python3 .claude/flow/state.py init
# 建立本次的節點紀錄目錄（flow-records/<開始時間>/），快照 spec 與 config
python3 .claude/flow/record.py init
