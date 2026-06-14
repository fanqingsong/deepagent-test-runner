import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

const coreRoutes: Array<[string, string]> = [
  ["#dashboard", "Test Dashboard heading"],
  ["#test-cases-marketplace", "Test Case Marketplace heading"],
  ["#test-cases", "test case list or + New Test"],
  ["#suites-marketplace", "Test Suite Marketplace heading"],
  ["#suites", "suite list or + New Suite"],
];

const tokenRoutes: Array<[string, string]> = [
  ["#token-usage", "Token Usage Dashboard heading"],
  ["#token-budget", "Budget Management"],
  ["#token-quota", "Quota Management"],
  ["#token-alert", "Alert Management"],
  ["#token-analytics", "Token Analytics"],
];

const adminRoutes: Array<[string, string]> = [
  ["#profile", "My Profile"],
  ["#users", "User Management"],
  ["#roles", "Role Management"],
  ["#reviews", "Review Management"],
  ["#chat-monitor", "Chat Monitor"],
  ["#monitoring", "System Monitoring"],
  ["#nanjing-weather", "weather page with 天气"],
];

function routeSteps(routes: Array<[string, string]>): string[] {
  return routes.flatMap(([hash, label]) => [goTo(hash, hash), `Verify page shows ${label}`]);
}

shortest([...routeSteps(coreRoutes)], authPayload);

shortest([...routeSteps(tokenRoutes)], authPayload);

shortest([...routeSteps(adminRoutes)], authPayload);

