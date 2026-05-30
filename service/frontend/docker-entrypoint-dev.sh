#!/bin/sh
set -e

# Ensure node_modules matches package-lock.json.
# When a new dependency is added to package.json, the anonymous volume
# may hold stale node_modules. Reinstall if lock file is newer.
MARKER="/app/frontend/node_modules/.docker-dev-deps-ok"
NEED_INSTALL=0

if [ ! -f "$MARKER" ]; then
  NEED_INSTALL=1
elif [ -f /app/frontend/package-lock.json ] && [ /app/frontend/package-lock.json -nt "$MARKER" ]; then
  NEED_INSTALL=1
fi

if [ "$NEED_INSTALL" = "1" ]; then
  echo "Installing dependencies in container..."
  if [ -d /app/frontend/node_modules ] && [ -n "$(ls -A /app/frontend/node_modules 2>/dev/null)" ]; then
    rm -rf /app/frontend/node_modules/*
  fi
  npm install --no-audit --no-fund
  touch "$MARKER"
  echo "Dependencies installed."
fi

echo "Starting Vite dev server..."
exec npm run dev -- --host 0.0.0.0
