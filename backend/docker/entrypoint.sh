#!/bin/sh
# migration 失敗即停止；以 exec 讓 uvicorn 直接接收容器停止訊號。
set -eu

# ChatGPT 憑證與新建資料檔僅限執行帳號讀寫。
umask 077
python -m alembic upgrade head
exec "$@"
