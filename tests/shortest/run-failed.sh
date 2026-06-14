#!/usr/bin/env bash
# Rerun tests that failed in the latest batch summary.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
SUMMARY="${1:-$DIR/results/latest-summary.txt}"
if [[ ! -f "$SUMMARY" ]]; then
  echo "No summary found: $SUMMARY" >&2
  exit 1
fi
mapfile -t failed < <(grep '^\[FAIL\]' "$SUMMARY" | sed -n 's/^\[FAIL\] \([^ ]*\).*/\1/p')
if [[ ${#failed[@]} -eq 0 ]]; then
  echo "No failed tests in $SUMMARY"
  exit 0
fi
echo "Rerunning ${#failed[@]} failed test(s)..."
for f in "${failed[@]}"; do
  echo ""
  ./run-one.sh "$f" 900 || true
  sleep 20
done
