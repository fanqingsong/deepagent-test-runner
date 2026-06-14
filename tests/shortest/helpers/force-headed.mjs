/** Force Playwright headed when SHORTEST_HEADLESS is not true. */
import { chromium } from "playwright";

if (process.env.SHORTEST_HEADLESS !== "true") {
  const launch = chromium.launch.bind(chromium);
  chromium.launch = (options = {}) =>
    launch({
      ...options,
      headless: false,
      slowMo: 300,
      args: ["--start-maximized", "--window-position=80,80", ...(options.args ?? [])],
    });
}
