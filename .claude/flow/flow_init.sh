#!/bin/bash
# 開始新的一次流程：清掉上一次的過程紀錄（程式與測試目錄不清，由角色覆寫）
set -eu
cd "$(dirname "$0")/../.."
# spec 必須經人確認、且確認後未被修改，否則不開始
python3 .claude/flow/state.py check_spec
rm -rf .flow
python3 .claude/flow/state.py init
