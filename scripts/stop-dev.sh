#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/tmp/run"

stop_process() {
  local name="$1"
  local pidfile="$RUN_DIR/$name.pid"

  if [[ ! -f "$pidfile" ]]; then
    echo "$name not running"
    return
  fi

  local pid
  pid="$(cat "$pidfile")"

  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    echo "stopped $name pid $pid"
  else
    echo "$name pid $pid already dead"
  fi

  rm -f "$pidfile"
}

stop_process "miniapp"
stop_process "bot"
stop_process "api"
stop_process "docgen"
