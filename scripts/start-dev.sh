#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/tmp/run"
LOG_DIR="$ROOT_DIR/tmp/logs"

mkdir -p "$RUN_DIR" "$LOG_DIR"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  echo "Missing .venv. Create it first:"
  echo "  cd $ROOT_DIR && python3 -m venv .venv && .venv/bin/pip install -e apps/api"
  exit 1
fi

if [[ ! -d "$ROOT_DIR/apps/docgen/node_modules" ]]; then
  echo "Missing docgen dependencies. Install first:"
  echo "  cd $ROOT_DIR/apps/docgen && npm install"
  exit 1
fi

if [[ ! -d "$ROOT_DIR/apps/miniapp/node_modules" ]]; then
  echo "Missing miniapp dependencies. Install first:"
  echo "  cd $ROOT_DIR/apps/miniapp && npm install"
  exit 1
fi

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_TEST_CHAT_ID="${TELEGRAM_TEST_CHAT_ID:-8134372922}"
SERVICE_URL_GOTENBERG="${SERVICE_URL_GOTENBERG:-https://gotenberg.alchin.kz}"
SERVICE_USER_GOTENBERG="${SERVICE_USER_GOTENBERG:-}"
SERVICE_PASSWORD_GOTENBERG="${SERVICE_PASSWORD_GOTENBERG:-}"
JWT_SECRET="${JWT_SECRET:-change-me}"
TELEGRAM_APP_URL="${TELEGRAM_APP_URL:-http://127.0.0.1:5173}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://127.0.0.1:5173}"
DOCGEN_URL="${DOCGEN_URL:-http://127.0.0.1:4001}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:8000}"
VITE_TELEGRAM_TEST_CHAT_ID="${VITE_TELEGRAM_TEST_CHAT_ID:-$TELEGRAM_TEST_CHAT_ID}"

kill_port_listener() {
  local port="$1"
  local pids
  pids="$(ss -ltnp "( sport = :$port )" 2>/dev/null | sed -n '2,$p' | sed -E 's/.*pid=([0-9]+).*/\1/' | sort -u)"

  if [[ -z "$pids" ]]; then
    return
  fi

  for pid in $pids; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
      fi
      echo "cleared pid $pid from port $port"
    fi
  done
}

start_process() {
  local name="$1"
  local cmd="$2"
  local workdir="$3"
  local pidfile="$RUN_DIR/$name.pid"
  local logfile="$LOG_DIR/$name.log"

  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running with pid $(cat "$pidfile")"
    return
  fi

  (
    cd "$workdir"
    nohup bash -lc "$cmd" </dev/null >"$logfile" 2>&1 &
    echo $! >"$pidfile"
  )

  echo "started $name pid $(cat "$pidfile")"
}

kill_port_listener 4001
kill_port_listener 8000
kill_port_listener 5173

start_process \
  "docgen" \
  "'$ROOT_DIR/apps/docgen/node_modules/.bin/tsx' watch src/index.ts" \
  "$ROOT_DIR/apps/docgen"

start_process \
  "api" \
  "TELEGRAM_BOT_TOKEN='$TELEGRAM_BOT_TOKEN' DOCGEN_URL='$DOCGEN_URL' SERVICE_URL_GOTENBERG='$SERVICE_URL_GOTENBERG' SERVICE_USER_GOTENBERG='$SERVICE_USER_GOTENBERG' SERVICE_PASSWORD_GOTENBERG='$SERVICE_PASSWORD_GOTENBERG' TELEGRAM_APP_URL='$TELEGRAM_APP_URL' FRONTEND_ORIGIN='$FRONTEND_ORIGIN' JWT_SECRET='$JWT_SECRET' '$ROOT_DIR/.venv/bin/uvicorn' app.main:app --app-dir '$ROOT_DIR/apps/api/src' --host 127.0.0.1 --port 8000 --reload" \
  "$ROOT_DIR"

if [[ -n "$TELEGRAM_BOT_TOKEN" ]]; then
  start_process \
    "bot" \
    "TELEGRAM_BOT_TOKEN='$TELEGRAM_BOT_TOKEN' TELEGRAM_APP_URL='$TELEGRAM_APP_URL' PYTHONPATH='$ROOT_DIR/apps/api/src' '$ROOT_DIR/.venv/bin/python' -m app.telegram_bot_runner" \
    "$ROOT_DIR"
else
  echo "bot skipped: TELEGRAM_BOT_TOKEN is empty"
fi

start_process \
  "miniapp" \
  "VITE_API_BASE_URL='$VITE_API_BASE_URL' VITE_TELEGRAM_TEST_CHAT_ID='$VITE_TELEGRAM_TEST_CHAT_ID' npm run dev -- --host 127.0.0.1 --port 5173" \
  "$ROOT_DIR/apps/miniapp"

echo
echo "Local URLs:"
echo "  Frontend: http://127.0.0.1:5173"
echo "  API:      http://127.0.0.1:8000"
echo "  Docgen:   http://127.0.0.1:4001"
echo
echo "Logs:"
echo "  tail -f $LOG_DIR/api.log"
echo "  tail -f $LOG_DIR/miniapp.log"
