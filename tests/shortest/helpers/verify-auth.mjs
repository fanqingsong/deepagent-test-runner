import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ storageState: ".shortest/auth-state.json" });
const page = await ctx.newPage();
await page.goto("http://localhost:8085/#dashboard", {
  waitUntil: "domcontentloaded",
  timeout: 30000,
});
console.log("url:", page.url());
console.log("dashboard visible:", await page.getByText("Test Dashboard").first().isVisible().catch(() => false));
await browser.close();
