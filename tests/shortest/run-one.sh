#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
FILE="${1:?Usage: ./run-one.sh <file.test.ts>}"
TIMEOUT_SEC="${2:-900}"
set -a
source .env.local
set +a
export SHORTEST_HEADLESS="${SHORTEST_HEADLESS:-true}"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q deepagent-tester-redis; then
  docker exec deepagent-tester-redis redis-cli KEYS 'ratelimit:login:*' 2>/dev/null \
    | xargs -r docker exec deepagent-tester-redis redis-cli DEL >/dev/null 2>&1 || true
fi
base="$(basename "$FILE" .test.ts)"
log="$DIR/results/debug-${base}-$(date +%H%M%S).log"
mkdir -p "$DIR/results"
echo "Running $FILE (timeout ${TIMEOUT_SEC}s) -> $log"
set +e
timeout "$TIMEOUT_SEC" npx shortest "$FILE" --headless >"$log" 2>&1
code=$?
set -e
grep -E "Tests|failed|passed|Error processing|Duration" "$log" | tail -8
echo "Exit: $code | Full log: $log"
