import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#test-cases-marketplace", "Test Case Marketplace"),
    "Verify Test Case Marketplace heading is visible",
    "Verify marketplace shows test case cards or an empty state message",
  ],
  authPayload,
);
