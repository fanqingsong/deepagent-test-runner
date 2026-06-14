import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";
import { assertAfterNavigate, assertAfterNavigateAny } from "./helpers/prompts";

const single = (text: string) => assertAfterNavigate(text);
const anyOf = (...texts: string[]) => assertAfterNavigateAny(...texts);

const coreRoutes: Array<[string, () => string]> = [
  ["#dashboard", () => single("Test Dashboard")],
  ["#test-cases-marketplace", () => single("Test Case Marketplace")],
  ["#test-cases", () => anyOf("+ New Test", "test case")],
  ["#suites-marketplace", () => single("Test Suite Marketplace")],
  ["#suites", () => anyOf("+ New Suite", "suite")],
];

const tokenRoutes: Array<[string, () => string]> = [
  ["#token-usage", () => single("Token Usage Dashboard")],
  ["#token-budget", () => single("Budget Management")],
  ["#token-quota", () => single("Quota Management")],
  ["#token-alert", () => single("Alert Management")],
  ["#token-analytics", () => single("Token Analytics")],
];

const adminRoutes: Array<[string, () => string]> = [
  ["#profile", () => single("My Profile")],
  ["#users", () => single("User Management")],
  ["#roles", () => single("Role Management")],
  ["#reviews", () => single("Review Management")],
  ["#chat-monitor", () => single("Chat Monitor")],
  ["#monitoring", () => single("System Monitoring")],
  ["#nanjing-weather", () => anyOf("天气", "Nanjing")],
];

function routeSteps(routes: Array<[string, () => string]>): string[] {
  return routes.flatMap(([hash, verify]) => [goTo(hash, hash), verify()]);
}

shortest([...routeSteps(coreRoutes)], authPayload);

shortest([...routeSteps(tokenRoutes)], authPayload);

shortest([...routeSteps(adminRoutes)], authPayload);
