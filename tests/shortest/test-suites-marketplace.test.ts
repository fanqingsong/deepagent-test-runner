import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#suites-marketplace", "Test Suite Marketplace"),
    "Verify Test Suite Marketplace heading is visible",
    "Verify marketplace shows suite cards or an empty state message",
  ],
  authPayload,
);
