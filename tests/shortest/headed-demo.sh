#!/usr/bin/env bash
# Open a visible browser window for 30s — run this in YOUR terminal (not agent background).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

set -a
# shellcheck disable=SC1091
source .env.local
set +a

export DISPLAY="${DISPLAY:-:0}"
export SHORTEST_HEADLESS=false
export NODE_OPTIONS="--import ${DIR}/helpers/force-headed.mjs${NODE_OPTIONS:+ $NODE_OPTIONS}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"

HASH="${1:-#chat-monitor}"
BASE="${BASE_URL:-http://localhost:8085}"
URL="${BASE%/}${HASH}"

echo "=========================================="
echo " 有界面演示：请在 Windows 任务栏找 Chromium 窗口"
echo " URL: $URL"
echo " 窗口将保持 30 秒后自动关闭"
echo "=========================================="

node --input-type=module << NODE
import { chromium } from 'playwright';
import { existsSync } from 'fs';

const statePath = '$DIR/.shortest/auth-state.json';
const url = '$URL';
const browser = await chromium.launch({
  headless: false,
  slowMo: 400,
  args: ['--start-maximized', '--window-position=0,0'],
});
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  ...(existsSync(statePath) ? { storageState: statePath } : {}),
  viewport: { width: 1400, height: 900 },
});
const page = await context.newPage();
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
console.log('Browser open — look for Chromium on your Windows taskbar');
await page.waitForTimeout(30000);
await browser.close();
NODE
