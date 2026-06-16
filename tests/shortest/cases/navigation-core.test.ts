import { shortest } from "@antiwork/shortest";
import { authPayload, navAndVerify } from "../helpers/flows";

type Route = [hash: string, title: string, ...matchTexts: string[]];

const coreRoutes: Route[] = [
  ["#dashboard", "Test Dashboard", "Test Dashboard"],
  ["#test-cases-marketplace", "Test Case Marketplace", "Test Case Marketplace", "Marketplace"],
  ["#test-cases", "Test Cases", "+ New Test", "test case", "Select or create a test case"],
  ["#suites-marketplace", "Test Suite Marketplace", "Test Suite Marketplace", "Marketplace"],
  ["#suites", "Test Suites", "+ New Suite", "suite", "No suites"],
];

for (const [hash, title, ...texts] of coreRoutes) {
  shortest([navAndVerify(hash, title, ...texts)], authPayload);
}
