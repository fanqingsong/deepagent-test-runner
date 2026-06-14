#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# shellcheck disable=SC1091
source "$DIR/helpers/run-common.sh"

set -a
# shellcheck disable=SC1091
source .env.local
set +a
export SHORTEST_HEADLESS=true

COOLDOWN_SEC="${COOLDOWN_SEC:-10}"
BETWEEN_FILES_SEC="${BETWEEN_FILES_SEC:-3}"

run_shortest_file() {
  local f="$1"
  local log="$2"
  shortest_env_for_file "$f"
  clear_login_ratelimit
  echo "SHORTEST_START_HASH=${SHORTEST_START_HASH:-}" >>"$log"
  timeout 900 npx shortest "$f" --headless >>"$log" 2>&1
}

setup_auth_state "$DIR" || true
kill_stale_shortest

RUN_ID="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$DIR/results/$RUN_ID"
mkdir -p "$OUT_DIR"

RESULTS="$OUT_DIR/summary.txt"
LATEST_LINK="$DIR/results/latest"

shopt -s nullglob
mapfile -t files < <(printf '%s\n' *.test.ts | sort)
total=${#files[@]}
pass=0
fail=0
idx=0

echo "Run ID: $RUN_ID" | tee "$RESULTS"
echo "Output: $OUT_DIR" | tee -a "$RESULTS"
echo "Running $total test files (headless, auth-state)..." | tee -a "$RESULTS"

for f in "${files[@]}"; do
  idx=$((idx + 1))
  base="$(basename "$f" .test.ts)"
  log="$OUT_DIR/${base}.log"

  echo "" | tee -a "$RESULTS"
  echo "========== [$idx/$total] $f ==========" | tee -a "$RESULTS"
  echo "Started: $(date -Iseconds)" >>"$log"

  set +e
  run_shortest_file "$f" "$log"
  exit_code=$?
  status="$(classify_log "$log")"
  if [[ "$status" == "FAIL" ]]; then
    echo "Retrying $f after cooldown..." | tee -a "$RESULTS"
    echo "--- RETRY ---" >>"$log"
    sleep "$COOLDOWN_SEC"
    run_shortest_file "$f" "$log"
    exit_code=$?
    status="$(classify_log "$log")"
  fi
  set -e

  echo "Exit code: $exit_code" >>"$log"
  echo "Finished: $(date -Iseconds)" >>"$log"
  if [[ "$status" == "PASS" ]]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
  fi

  summary=$(grep -E "Tests[[:space:]]+[0-9]+ passed|Error processing|Duration" "$log" | tail -5 | tr '\n' ' ')
  echo "[$status] $f — ${summary:-see $log}" | tee -a "$RESULTS"
  sleep "$BETWEEN_FILES_SEC"
done

echo "" | tee -a "$RESULTS"
echo "========== SUMMARY ==========" | tee -a "$RESULTS"
echo "Total: $total  Passed: $pass  Failed: $fail" | tee -a "$RESULTS"
echo "Finished: $(date -Iseconds)" | tee -a "$RESULTS"
echo "Logs: $OUT_DIR/" | tee -a "$RESULTS"

ln -sfn "$RUN_ID" "$LATEST_LINK"
cp "$RESULTS" "$DIR/results/latest-summary.txt"

[[ "$fail" -eq 0 ]]
