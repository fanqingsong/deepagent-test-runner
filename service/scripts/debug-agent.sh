#!/usr/bin/env bash
# Debug Deep Agent — inspect thread state, store, and run logs
#
# Usage:
#   ./scripts/debug-agent.sh                  # List all threads
#   ./scripts/debug-agent.sh <thread_id>      # Show thread state (todos, files, messages)
#   ./scripts/debug-agent.sh store            # Show all store namespaces and items
#   ./scripts/debug-agent.sh store <ns>       # Show items in a namespace (e.g. "user/1")
#   ./scripts/debug-agent.sh store <ns> <key> # Read a specific store item
#   ./scripts/debug-agent.sh runs <thread_id> # List runs for a thread
#   ./scripts/debug-agent.sh history <thread_id> # Show state checkpoint history
#   ./scripts/debug-agent.sh log              # Tail langgraph-server logs
#
# Environment:
#   LANGGRAPH_URL  — LangGraph server URL (default: http://localhost:2024)
#   USER_ID        — User ID for token (default: 1)

set -euo pipefail

LANGGRAPH_URL="${LANGGRAPH_URL:-http://localhost:2024}"
BACKEND_CONTAINER="deepagent-tester-backend"
LANGGRAPH_CONTAINER="deepagent-tester-langgraph"
USER_ID="${USER_ID:-1}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

get_token() {
  docker exec "$BACKEND_CONTAINER" python3 -c "
from app.core.security import create_access_token
print(create_access_token({'sub': '${USER_ID}'}))
" 2>/dev/null
}

api() {
  local method="$1" path="$2" body="${3:-}"
  local token
  token=$(get_token)
  local args=(-s -H "Authorization: Bearer $token" -H "Content-Type: application/json")
  if [ "$method" = "GET" ]; then
    curl "${args[@]}" "${LANGGRAPH_URL}${path}"
  else
    curl "${args[@]}" -X "$method" "${LANGGRAPH_URL}${path}" -d "${body}"
  fi
}

cmd_threads() {
  echo -e "${BOLD}Threads (limit 20)${RESET}"
  echo -e "${DIM}─────────────────────────────────────────────────${RESET}"
  api POST /threads/search '{"limit": 20}' | python3 -c "
import json, sys
try:
    threads = json.load(sys.stdin)
except:
    print('  (no data)')
    sys.exit(0)
if not threads:
    print('  No threads found')
    sys.exit(0)
for t in threads:
    tid = t.get('thread_id', '?')[:12]
    title = (t.get('metadata') or {}).get('title', 'Untitled')
    status = t.get('status', '?')
    updated = t.get('updated_at', '')[:19]
    msgs = len(t.get('values', {}).get('messages', []))
    todos = t.get('values', {}).get('todos', [])
    todo_summary = ''
    if todos:
        done = sum(1 for x in todos if x.get('status') == 'completed')
        todo_summary = f'  todos={done}/{len(todos)}'
    print(f'  ${CYAN}{tid}${RESET}  {title}')
    print(f'          status={status}  msgs={msgs}{todo_summary}  updated={updated}')
    print()
"
}

cmd_state() {
  local thread_id="$1"
  echo -e "${BOLD}Thread State: ${thread_id}${RESET}"
  echo -e "${DIM}─────────────────────────────────────────────────${RESET}"
  api GET "/threads/${thread_id}/state" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except:
    print('  (failed to load state)')
    sys.exit(1)

values = data.get('values', {})

# Todos
todos = values.get('todos', [])
print(f'\n${BOLD}Todos ({len(todos)})${RESET}')
if not todos:
    print('  (none)')
for t in todos:
    status = t.get('status', '?')
    content = t.get('content', '')
    icon = {'pending': '○', 'in_progress': '◉', 'completed': '✓'}.get(status, '?')
    color = {'pending': '${DIM}', 'in_progress': '${YELLOW}', 'completed': '${GREEN}'}.get(status, '')
    print(f'  {color}{icon}${RESET} [{status:12s}] {content}')

# Files
files = values.get('files', {})
print(f'\n${BOLD}Files ({len(files)})${RESET}')
if not files:
    print('  (none)')
for path, content in files.items():
    text = str(content)
    if len(text) > 500:
        text = text[:500] + '...'
    print(f'  ${CYAN}{path}${RESET}')
    for line in text.split('\n'):
        print(f'    {line}')
    print()

# Messages summary
msgs = values.get('messages', [])
print(f'\n${BOLD}Messages ({len(msgs)})${RESET}')
for i, m in enumerate(msgs):
    t = m.get('type', '?')
    c = str(m.get('content', ''))
    c = c.replace('\n', ' ')[:120]
    tcs = m.get('tool_calls', [])
    tool_info = ''
    if tcs:
        names = [tc.get('name', '?') for tc in tcs]
        tool_info = f' [tools: {\", \".join(names)}]'
    color = {'human': '${BOLD}', 'ai': '${GREEN}', 'tool': '${DIM}'}.get(t, '')
    print(f'  {color}[{t:5s}]${RESET} {c}{tool_info}')
print()
"
}

cmd_store() {
  local ns="${1:-}" key="${2:-}"

  if [ -z "$ns" ]; then
    echo -e "${BOLD}Store Namespaces${RESET}"
    echo -e "${DIM}─────────────────────────────────────────────────${RESET}"
    api POST /store/namespaces '{}' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except:
    print('  (failed)')
    sys.exit(1)
nss = data.get('namespaces', [])
if not nss:
    print('  (empty)')
for ns in nss:
    path = '/'.join(ns) if isinstance(ns, list) else str(ns)
    print(f'  ${CYAN}{path}${RESET}')
"
  elif [ -z "$key" ]; then
    local ns_json
    ns_json=$(echo "$ns" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read().strip().split('/')))")
    echo -e "${BOLD}Store Items: ${ns}${RESET}"
    echo -e "${DIM}─────────────────────────────────────────────────${RESET}"
    api POST /store/items/search "{\"namespace_prefix\": ${ns_json}}" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except:
    print('  (failed)')
    sys.exit(1)
items = data.get('items', [])
if not items:
    print('  (empty)')
for item in items:
    k = item.get('key', '?')
    val = item.get('value', {})
    text = json.dumps(val, ensure_ascii=False)
    if len(text) > 500:
        text = text[:500] + '...'
    print(f'  ${CYAN}{k}${RESET}')
    print(f'    {text}')
    print()
"
  else
    local ns_json
    ns_json=$(echo "$ns" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read().strip().split('/')))")
    echo -e "${BOLD}Store Item: ${ns}/${key}${RESET}"
    echo -e "${DIM}─────────────────────────────────────────────────${RESET}"
    local encoded_ns
    encoded_ns=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${ns}', safe=''))")
    api GET "/store/items?namespace=${encoded_ns}&key=${key}" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except:
    data = sys.stdin.read()
    print(f'  {data}')
    sys.exit(0)
if data is None:
    print('  (not found)')
else:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    print(text)
"
  fi
}

cmd_runs() {
  local thread_id="$1"
  echo -e "${BOLD}Runs for thread: ${thread_id}${RESET}"
  echo -e "${DIM}─────────────────────────────────────────────────${RESET}"
  api GET "/threads/${thread_id}/runs" | python3 -c "
import json, sys
try:
    runs = json.load(sys.stdin)
except:
    print('  (failed)')
    sys.exit(1)
if not runs:
    print('  No runs')
for r in runs:
    rid = r.get('run_id', '?')[:12]
    status = r.get('status', '?')
    created = r.get('created_at', '')[:19]
    print(f'  ${CYAN}{rid}${RESET}  status={status}  created={created}')
"
}

cmd_history() {
  local thread_id="$1"
  echo -e "${BOLD}State History: ${thread_id}${RESET}"
  echo -e "${DIM}─────────────────────────────────────────────────${RESET}"
  api GET "/threads/${thread_id}/history" | python3 -c "
import json, sys
try:
    history = json.load(sys.stdin)
except:
    print('  (failed)')
    sys.exit(1)
if not history:
    print('  No history')
    sys.exit(0)
for i, checkpoint in enumerate(history):
    cid = checkpoint.get('checkpoint_id', '?')[:12]
    ts = checkpoint.get('created_at', '')[:19]
    vals = checkpoint.get('values', {})
    todos = vals.get('todos', [])
    todo_str = ''
    if todos:
        done = sum(1 for x in todos if x.get('status') == 'completed')
        todo_str = f'  todos={done}/{len(todos)}'
    msgs = len(vals.get('messages', []))
    files = len(vals.get('files', {}))
    print(f'  #{i:2d}  ${CYAN}{cid}${RESET}  msgs={msgs}  files={files}{todo_str}  {ts}')
"
}

cmd_log() {
  echo -e "${BOLD}LangGraph Server Logs (tail -f)${RESET}"
  echo -e "${DIM}─────────────────────────────────────────────────${RESET}"
  echo -e "  ${DIM}Press Ctrl+C to stop${RESET}"
  echo ""
  docker logs -f "$LANGGRAPH_CONTAINER" 2>&1
}

# Main
case "${1:-}" in
  "")
    cmd_threads
    ;;
  store)
    cmd_store "${2:-}" "${3:-}"
    ;;
  runs)
    if [ -z "${2:-}" ]; then echo "Usage: $0 runs <thread_id>"; exit 1; fi
    cmd_runs "$2"
    ;;
  history)
    if [ -z "${2:-}" ]; then echo "Usage: $0 history <thread_id>"; exit 1; fi
    cmd_history "$2"
    ;;
  log)
    cmd_log
    ;;
  help|--help|-h)
    echo "Debug Deep Agent — inspect thread state, store, and run logs"
    echo ""
    echo "Usage:"
    echo "  $0                            List all threads"
    echo "  $0 <thread_id>                Show thread state (todos, files, messages)"
    echo "  $0 store                      Show all store namespaces"
    echo "  $0 store <namespace>          Show items in namespace (e.g. user/1)"
    echo "  $0 store <namespace> <key>    Read a specific store item"
    echo "  $0 runs <thread_id>           List runs for a thread"
    echo "  $0 history <thread_id>        Show state checkpoint history"
    echo "  $0 log                        Tail langgraph-server logs"
    echo ""
    echo "Environment:"
    echo "  LANGGRAPH_URL   LangGraph server URL (default: http://localhost:2024)"
    echo "  USER_ID         User ID for token (default: 1)"
    ;;
  *)
    cmd_state "$1"
    ;;
esac
