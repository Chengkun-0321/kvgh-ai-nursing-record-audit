#!/usr/bin/env bash
# 一鍵啟動／關閉開發環境（後端 FastAPI + 前端 Next.js）。
#
# 用法：scripts/dev.sh start | stop | restart | status
# 環境變數：DEV_DB_NAME 指定 backend/data/<名稱>.db（未設定時用後端設定的預設資料庫）；
#           BACKEND_PORT、FRONTEND_PORT 可改連接埠（改後端連接埠時 frontend/.env.local 要一併調整）。
# 服務在背景執行；PID 與 log 放在 .run/（不進版控）。
# 只會停止本腳本啟動的程序，不會動到其他占用同一連接埠的程式。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
READY_TIMEOUT_SECONDS=60
STOP_TIMEOUT_SECONDS=10

pid_file() { echo "$RUN_DIR/$1.pid"; }
log_file() { echo "$RUN_DIR/$1.log"; }

# 讀出仍在執行的 PID；程序已不存在時清掉殘留的 PID 檔
running_pid() {
  local file pid
  file="$(pid_file "$1")"
  [ -f "$file" ] || return 1
  pid="$(cat "$file")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "$pid"
    return 0
  fi
  rm -f "$file"
  return 1
}

is_port_listening() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# 連接埠已被別的程式占用時不啟動，避免誤以為啟動成功
require_free_port() {
  if is_port_listening "$2"; then
    echo "✗ ${1}：連接埠 $2 已被其他程式占用，請先關閉它（lsof -nP -iTCP:$2 -sTCP:LISTEN）" >&2
    return 1
  fi
}

wait_until_ready() {
  local name="$1" port="$2" waited=0
  while [ "$waited" -lt "$READY_TIMEOUT_SECONDS" ]; do
    if ! running_pid "$name" >/dev/null; then
      echo "✗ $name 啟動失敗，最後的 log：" >&2
      tail -n 20 "$(log_file "$name")" >&2
      return 1
    fi
    if is_port_listening "$port"; then
      echo "✓ $name 已啟動：http://localhost:${port}（log：.run/$name.log）"
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  echo "✗ $name 在 $READY_TIMEOUT_SECONDS 秒內沒有開始監聽連接埠 ${port}，請查看 .run/$name.log" >&2
  return 1
}

check_prerequisites() {
  local missing=0
  if [ ! -x "$ROOT_DIR/backend/.venv/bin/python" ]; then
    echo "✗ 找不到 backend/.venv，請依 backend/CLAUDE.md 建立虛擬環境" >&2
    missing=1
  fi
  if [ ! -f "$ROOT_DIR/backend/.env" ]; then
    echo "✗ 找不到 backend/.env，請複製 backend/.env.example 並填入 LLM_KEY_ENCRYPTION_KEY" >&2
    missing=1
  fi
  if [ ! -x "$ROOT_DIR/frontend/node_modules/.bin/next" ]; then
    echo "✗ 找不到 frontend/node_modules，請在 frontend/ 執行 npm install" >&2
    missing=1
  fi
  if [ ! -f "$ROOT_DIR/frontend/.env.local" ]; then
    echo "✗ 找不到 frontend/.env.local，請複製 frontend/.env.example" >&2
    missing=1
  fi
  return "$missing"
}

start_backend() {
  if running_pid backend >/dev/null; then
    echo "• backend 已在執行（PID $(running_pid backend)）"
    return 0
  fi
  require_free_port backend "$BACKEND_PORT"
  (
    cd "$ROOT_DIR/backend"
    # 各分支的 migration 不同時，可用 DEV_DB_NAME 讓每個分支使用各自的資料庫檔
    if [ -n "${DEV_DB_NAME:-}" ]; then
      export DATABASE_URL="sqlite+aiosqlite:///$PWD/data/$DEV_DB_NAME.db"
    fi
    .venv/bin/python -m alembic upgrade head
    # exec 讓 PID 檔記錄的就是 uvicorn 本身，關閉時才能直接送訊號
    exec .venv/bin/python -m uvicorn app.main:app --reload --port "$BACKEND_PORT"
  ) >"$(log_file backend)" 2>&1 &
  echo $! >"$(pid_file backend)"
  wait_until_ready backend "$BACKEND_PORT"
}

start_frontend() {
  if running_pid frontend >/dev/null; then
    echo "• frontend 已在執行（PID $(running_pid frontend)）"
    return 0
  fi
  require_free_port frontend "$FRONTEND_PORT"
  (
    cd "$ROOT_DIR/frontend"
    exec node_modules/.bin/next dev --port "$FRONTEND_PORT"
  ) >"$(log_file frontend)" 2>&1 &
  echo $! >"$(pid_file frontend)"
  wait_until_ready frontend "$FRONTEND_PORT"
}

# 由葉節點往上列出整棵程序樹（uvicorn --reload 與 next dev 都會再開子程序）
process_tree() {
  local child
  for child in $(pgrep -P "$1" 2>/dev/null || true); do
    process_tree "$child"
  done
  echo "$1"
}

any_alive() {
  local pid
  for pid in "$@"; do
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  done
  return 1
}

stop_service() {
  local name="$1" pid pids waited=0
  if ! pid="$(running_pid "$name")"; then
    echo "• $name 沒有在執行"
    return 0
  fi
  pids="$(process_tree "$pid")"
  # shellcheck disable=SC2086  # 刻意分詞：pids 是以空白分隔的 PID 清單
  kill $pids 2>/dev/null || true
  # shellcheck disable=SC2086
  while any_alive $pids && [ "$waited" -lt "$STOP_TIMEOUT_SECONDS" ]; do
    sleep 1
    waited=$((waited + 1))
  done
  # shellcheck disable=SC2086
  if any_alive $pids; then
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
  fi
  rm -f "$(pid_file "$name")"
  echo "✓ $name 已關閉"
}

show_status() {
  local name port pid
  for name in backend frontend; do
    port="$BACKEND_PORT"
    [ "$name" = frontend ] && port="$FRONTEND_PORT"
    if pid="$(running_pid "$name")"; then
      echo "✓ $name 執行中（PID ${pid}，http://localhost:${port}）"
    else
      echo "• $name 未執行"
    fi
  done
}

start_all() {
  check_prerequisites
  mkdir -p "$RUN_DIR"
  start_backend
  start_frontend
}

stop_all() {
  stop_service frontend
  stop_service backend
}

case "${1:-}" in
  start) start_all ;;
  stop) stop_all ;;
  restart) stop_all && start_all ;;
  status) show_status ;;
  *)
    echo "用法：scripts/dev.sh start | stop | restart | status" >&2
    exit 2
    ;;
esac
