#!/usr/bin/env bash
# Shared helpers for shortest batch runners.


CASES_DIR="${CASES_DIR:-cases}"

resolve_case_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    echo "$f"
  elif [[ -f "$CASES_DIR/$f" ]]; then
    echo "$CASES_DIR/$f"
  else
    echo "$f"
  fi
}

list_case_files() {
  local dir="${1:-$CASES_DIR}"
  shopt -s nullglob
  local f
  for f in "$dir"/*.test.ts; do
    printf '%s\n' "$f"
  done | sort
}

clear_login_ratelimit() {
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q deepagent-tester-redis; then
    docker exec deepagent-tester-redis redis-cli KEYS 'ratelimit*' 2>/dev/null \
      | xargs -r docker exec deepagent-tester-redis redis-cli DEL >/dev/null 2>&1 || true
  fi
}

setup_auth_state() {
  local dir="$1"
  clear_login_ratelimit
  if node "$dir/helpers/setup-auth.mjs"; then
    echo "Auth state ready: $dir/.shortest/auth-state.json"
    return 0
  fi
  echo "WARN: setup-auth failed; tests will fall back to AI login" >&2
  return 1
}

# Classify using the last run block (after --- RETRY --- if present).
classify_log() {
  local log="$1"
  local section
  if grep -q "--- RETRY ---" "$log" 2>/dev/null; then
    section="$(sed -n '/--- RETRY ---/,$p' "$log")"
  else
    section="$(cat "$log")"
  fi
  if echo "$section" | grep -q "Error processing file"; then
    echo "FAIL"
  elif echo "$section" | grep -qE "[0-9]+ failed"; then
    echo "FAIL"
  elif echo "$section" | grep -qE "Tests[[:space:]]+0 passed"; then
    echo "FAIL"
  elif echo "$section" | grep -qE "Tests[[:space:]]+[1-9][0-9]* passed"; then
    echo "PASS"
  else
    echo "FAIL"
  fi
}

shortest_env_for_file() {
  local f="$1"
  local helpers_dir
  helpers_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ "$(basename "$f")" == "login.test.ts" ]]; then
    export SHORTEST_SKIP_AUTH_STATE=1
    unset SHORTEST_START_HASH
  else
    unset SHORTEST_SKIP_AUTH_STATE
    local hash
    hash="$(node "$helpers_dir/route-hashes.mjs" "$(basename "$f")" 2>/dev/null || echo '#dashboard')"
    export SHORTEST_START_HASH="${hash:-#dashboard}"
  fi
}

kill_stale_shortest() {
  pkill -9 -f "node.*shortest.*\.test\.ts" 2>/dev/null || true
  sleep 1
}
