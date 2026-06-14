/** Per-file SPA hash for Playwright storageState + shortest baseUrl pre-navigation. */
export const ROUTE_HASHES = {
  "smoke.test.ts": "#dashboard",
  "dashboard.test.ts": "#dashboard",
  "chat-assistant.test.ts": "#dashboard",
  "chat-monitor.test.ts": "#chat-monitor",
  "monitoring.test.ts": "#monitoring",
  "nanjing-weather.test.ts": "#nanjing-weather",
  "profile.test.ts": "#profile",
  "users.test.ts": "#users",
  "roles.test.ts": "#roles",
  "reviews.test.ts": "#reviews",
  "test-cases.test.ts": "#test-cases",
  "test-cases-marketplace.test.ts": "#test-cases-marketplace",
  "test-suites.test.ts": "#suites",
  "test-suites-marketplace.test.ts": "#suites-marketplace",
  "token-usage.test.ts": "#token-usage",
  "token-budget.test.ts": "#token-budget",
  "token-quota.test.ts": "#token-quota",
  "token-alert.test.ts": "#token-alert",
  "token-analytics.test.ts": "#token-analytics",
  "navigation.test.ts": "#dashboard",
};

export function routeHashFor(filename) {
  return ROUTE_HASHES[filename] ?? "#dashboard";
}

if (process.argv[1]?.endsWith("route-hashes.mjs")) {
  const name = process.argv[2];
  if (name) process.stdout.write(routeHashFor(name));
}
