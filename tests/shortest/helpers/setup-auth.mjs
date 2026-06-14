#!/usr/bin/env node
/**
 * Fast Playwright login — saves storageState for subsequent shortest runs.
 * Avoids repeating AI-driven login in every test file.
 */
import { chromium } from "playwright";
import { mkdirSync, existsSync, readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

function loadEnvLocal() {
  const path = join(root, ".env.local");
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, "utf8").split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m && !process.env[m[1]]) {
      process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  }
}

loadEnvLocal();

const baseUrl = process.env.BASE_URL || "http://localhost:8085";
const email = process.env.E2E_EMAIL || "e2e@test.com";
const password = process.env.E2E_PASSWORD || "TestPass123!";
const outDir = join(root, ".shortest");
const statePath = join(outDir, "auth-state.json");

mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ ignoreHTTPSErrors: true });
const page = await context.newPage();

try {
  await page.goto(`${baseUrl}/#login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.getByRole("textbox", { name: /email/i }).fill(email);
  await page.getByRole("textbox", { name: /password/i }).fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/#(dashboard|test-cases|suites|token|profile|users)/, { timeout: 30000 });
  await context.storageState({ path: statePath });
  console.log(`Auth state saved: ${statePath}`);
} finally {
  await browser.close();
}
