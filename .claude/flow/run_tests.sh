#!/bin/bash
# ⑥ 跑測試：不經過 AI。依序執行 套件白名單檢查 → setup_command → test_command，
# 任何一步失敗就停止，該輪判為失敗。指令都來自 flow.config.json。
# 完整輸出只寫進 log，終端只印通過/失敗與 log 最後幾行摘要。
set -u
cd "$(dirname "$0")/../.."
N="${1:?用法：run_tests.sh <輪次>}"
LOG=".flow/runs/round-$N.log"
mkdir -p .flow/runs

SETUP=$(python3 .claude/flow/state.py config setup_command)
CMD=$(python3 .claude/flow/state.py config test_command)
NO_TESTS=$(python3 .claude/flow/state.py config no_tests_regex)
: > "$LOG"
RC=0

# 1. 套件白名單：沒通過就不安裝
echo "## [1/3] 套件白名單檢查" >> "$LOG"
python3 .claude/flow/state.py check_deps >> "$LOG" 2>&1 || RC=1

# 2. 安裝（選填）
if [ "$RC" -eq 0 ] && [ -n "$SETUP" ]; then
  echo "## [2/3] setup_command" >> "$LOG"
  { echo "\$ $SETUP"; bash -c "$SETUP"; } >> "$LOG" 2>&1 || { RC=1; echo "setup 失敗" >> "$LOG"; }
fi

# 3. 測試
if [ "$RC" -eq 0 ]; then
  echo "## [3/3] test_command" >> "$LOG"
  if [ -z "$CMD" ]; then
    echo "flow.config.json 缺少 test_command" >> "$LOG"
    RC=1
  else
    { echo "\$ $CMD"; bash -c "$CMD"; } >> "$LOG" 2>&1 || RC=1
    # 有些框架在 0 個測試時仍回傳 0，符合 no_tests_regex 時視為失敗
    if [ -n "$NO_TESTS" ] && grep -Eq "$NO_TESTS" "$LOG"; then RC=1; fi
  fi
fi

python3 .claude/flow/state.py test "$N" "$RC"
SUMMARY=$(tail -n 3 "$LOG" | tr '\n' ' ')
if [ "$RC" -eq 0 ]; then
  echo "第 $N 輪：通過。$SUMMARY（紀錄：$LOG）"
else
  echo "第 $N 輪：失敗。$SUMMARY（紀錄：$LOG）"
fi
exit 0
