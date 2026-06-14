#!/usr/bin/env bash
# Run all *.test.ts files in parallel (file-level concurrency).
#
# Usage:
#   ./run-all-parallel.sh              # default 2 workers
#   PARALLEL_JOBS=4 ./run-all-parallel.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# shellcheck disable=SC1091
source "$DIR/helpers/run-common.sh"

PARALLEL_JOBS="${PARALLEL_JOBS:-2}"
TIMEOUT_SEC="${TIMEOUT_SEC:-900}"
COOLDOWN_SEC="${COOLDOWN_SEC:-10}"

set -a
# shellcheck disable=SC1091
source .env.local
set +a
export SHORTEST_HEADLESS="${SHORTEST_HEADLESS:-false}"

headless_flag() {
  [[ "${SHORTEST_HEADLESS}" == "true" ]] && echo --headless
}

run_one_file() {
  local f="$1"
  local log="$2"

  {
    echo "Started: $(date -Iseconds)"
    shortest_env_for_file "$f"
    clear_login_ratelimit
    echo "SHORTEST_START_HASH=${SHORTEST_START_HASH:-}"
    timeout "$TIMEOUT_SEC" npx shortest "$f" $(headless_flag)
    local exit_code=$?
    local status
    status="$(classify_log "$log")"

    if [[ "$status" == "FAIL" ]]; then
      echo "--- RETRY ---"
      sleep "$COOLDOWN_SEC"
      shortest_env_for_file "$f"
      clear_login_ratelimit
      echo "SHORTEST_START_HASH=${SHORTEST_START_HASH:-}"
      timeout "$TIMEOUT_SEC" npx shortest "$f" $(headless_flag)
      exit_code=$?
      status="$(classify_log "$log")"
    fi

    echo "Exit code: $exit_code"
    echo "Finished: $(date -Iseconds)"
  } >>"$log" 2>&1

  local status
  status="$(classify_log "$log")"
  printf '%s\t%s\t%s\n' "$status" "$f" "$log"
}

export -f run_one_file classify_log clear_login_ratelimit shortest_env_for_file
export TIMEOUT_SEC SHORTEST_HEADLESS COOLDOWN_SEC

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

echo "Run ID: $RUN_ID" | tee "$RESULTS"
echo "Output: $OUT_DIR" | tee -a "$RESULTS"
echo "Running $total test files in parallel (jobs=$PARALLEL_JOBS, headless=${SHORTEST_HEADLESS}, auth-state)..." | tee -a "$RESULTS"

pass=0
fail=0
running=0

for f in "${files[@]}"; do
  base="$(basename "$f" .test.ts)"
  log="$OUT_DIR/${base}.log"
  : >"$log"

  run_one_file "$f" "$log" >>"$OUT_DIR/.results.tsv" &
  running=$((running + 1))

  if [[ "$running" -ge "$PARALLEL_JOBS" ]]; then
    wait -n
    running=$((running - 1))
  fi
done

wait

echo "" | tee -a "$RESULTS"
while IFS=$'\t' read -r status f log; do
  [[ -z "${f:-}" ]] && continue
  summary=$(grep -E "Tests[[:space:]]+[0-9]+ passed|Error processing|Duration" "$log" | tail -5 | tr '\n' ' ')
  echo "[$status] $f — ${summary:-see $log}" | tee -a "$RESULTS"
  if [[ "$status" == "PASS" ]]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
  fi
done < <(sort "$OUT_DIR/.results.tsv" 2>/dev/null || true)

echo "" | tee -a "$RESULTS"
echo "========== SUMMARY ==========" | tee -a "$RESULTS"
echo "Total: $total  Passed: $pass  Failed: $fail  Jobs: $PARALLEL_JOBS" | tee -a "$RESULTS"
echo "Finished: $(date -Iseconds)" | tee -a "$RESULTS"
echo "Logs: $OUT_DIR/" | tee -a "$RESULTS"

ln -sfn "$RUN_ID" "$LATEST_LINK"
cp "$RESULTS" "$DIR/results/latest-summary.txt"
rm -f "$OUT_DIR/.results.tsv"

[[ "$fail" -eq 0 ]]
