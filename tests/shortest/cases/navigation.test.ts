import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "../helpers/flows";
import { assertAfterNavigate, assertAfterNavigateAny } from "../helpers/prompts";

const single = (text: string) => assertAfterNavigate(text);
const anyOf = (...texts: string[]) => assertAfterNavigateAny(...texts);

const coreRoutes: Array<[string, string, () => string]> = [
  ["#dashboard", "Test Dashboard", () => single("Test Dashboard")],
  ["#test-cases-marketplace", "Test Case Marketplace", () => single("Test Case Marketplace")],
  ["#test-cases", "Test Cases", () => anyOf("+ New Test", "test case")],
  ["#suites-marketplace", "Test Suite Marketplace", () => single("Test Suite Marketplace")],
  ["#suites", "Test Suites", () => anyOf("+ New Suite", "suite")],
];

const tokenRoutes: Array<[string, string, () => string]> = [
  ["#token-usage", "Token Usage Dashboard", () => single("Token Usage Dashboard")],
  ["#token-budget", "Budget Management", () => single("Budget Management")],
  ["#token-quota", "Quota Management", () => single("Quota Management")],
  ["#token-alert", "Alert Management", () => single("Alert Management")],
  ["#token-analytics", "Token Analytics", () => single("Token Analytics")],
];

const adminRoutes: Array<[string, string, () => string]> = [
  ["#profile", "My Profile", () => single("My Profile")],
  ["#users", "User Management", () => single("User Management")],
  ["#roles", "Role Management", () => single("Role Management")],
  ["#reviews", "Review Management", () => single("Review Management")],
  ["#chat-monitor", "Chat Monitor", () => single("Chat Monitor")],
  ["#monitoring", "System Monitoring", () => single("System Monitoring")],
  ["#nanjing-weather", "Nanjing Weather", () => anyOf("天气", "Nanjing", "Weather")],
];

function routeSteps(routes: Array<[string, string, () => string]>): string[] {
  return routes.flatMap(([hash, title, verify]) => [goTo(hash, title), verify()]);
}

shortest([...routeSteps(coreRoutes)], authPayload);

shortest([...routeSteps(tokenRoutes)], authPayload);

shortest([...routeSteps(adminRoutes)], authPayload);
