#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
FILE="${1:?Usage: ./run-one.sh <file.test.ts> [timeout_sec] [--headless]}"
TIMEOUT_SEC=900
FORCE_HEADLESS=false

for arg in "${@:2}"; do
  case "$arg" in
    --headless) FORCE_HEADLESS=true ;;
    [0-9]*) TIMEOUT_SEC="$arg" ;;
  esac
done

# shellcheck disable=SC1091
source "$DIR/helpers/run-common.sh"

set -a
# shellcheck disable=SC1091
source .env.local
set +a

export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export SHORTEST_LOG_CONFIG=1

# Force headed — do NOT use ${SHORTEST_HEADLESS:-false} (inherits stale true from shell)
if [[ "$FORCE_HEADLESS" == "true" ]]; then
  export SHORTEST_HEADLESS=true
  unset NODE_OPTIONS
else
  export SHORTEST_HEADLESS=false
  export NODE_OPTIONS="--import ${DIR}/helpers/force-headed.mjs${NODE_OPTIONS:+ $NODE_OPTIONS}"
fi

headless_flag() {
  [[ "${SHORTEST_HEADLESS}" == "true" ]] && echo --headless
}

setup_auth_state "$DIR" || true
shortest_env_for_file "$FILE"
clear_login_ratelimit

base="$(basename "$FILE" .test.ts)"
log="$DIR/results/debug-${base}-$(date +%H%M%S).log"
mkdir -p "$DIR/results"

echo "=========================================="
if [[ "${SHORTEST_HEADLESS}" == "true" ]]; then
  echo " 无界面模式"
else
  echo " 有界面模式 — 看 Windows 任务栏 Chromium 窗口"
  echo " 演示: ./headed-demo.sh"
fi
echo " SHORTEST_HEADLESS=${SHORTEST_HEADLESS}"
echo " 文件: $FILE | 路由: ${SHORTEST_START_HASH:-默认} | 超时: ${TIMEOUT_SEC}s"
echo "=========================================="

echo "SHORTEST_START_HASH=${SHORTEST_START_HASH:-}" >>"$log"

set +e
if [[ "${SHORTEST_DEBUG:-}" == "1" ]]; then
  PWDEBUG=1 timeout "$TIMEOUT_SEC" npx shortest "$FILE" $(headless_flag) 2>&1 | tee "$log"
else
  timeout "$TIMEOUT_SEC" npx shortest "$FILE" $(headless_flag) 2>&1 | tee "$log"
fi
code=${PIPESTATUS[0]}
set -e

grep -E "Tests|failed|passed|Error processing|Duration|shortest.config" "$log" | tail -10 || true
echo "Exit: $code | Full log: $log"
