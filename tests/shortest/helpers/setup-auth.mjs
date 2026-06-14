#!/usr/bin/env node
/**
 * Fast Playwright login — saves storageState for subsequent shortest runs.
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

const baseUrl = (process.env.BASE_URL || "http://localhost:8085").replace(/\/$/, "");
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

  const loginError = page.locator("text=/invalid|failed|error|rate limit/i").first();
  await Promise.race([
    page.waitForFunction(
      () => {
        const hash = window.location.hash.replace(/^#/, "");
        return hash.length > 0 && hash !== "login";
      },
      { timeout: 60000 },
    ),
    page.getByRole("heading", { name: /Test Dashboard/i }).waitFor({ timeout: 60000 }),
    page.locator(".sidebar, nav").first().waitFor({ timeout: 60000 }),
  ]).catch(async () => {
    const errText = await loginError.textContent().catch(() => null);
    throw new Error(errText ? `Login failed: ${errText}` : "Login timed out waiting for post-auth page");
  });

  await context.storageState({ path: statePath });
  console.log(`Auth state saved: ${statePath}`);
} finally {
  await browser.close();
}
