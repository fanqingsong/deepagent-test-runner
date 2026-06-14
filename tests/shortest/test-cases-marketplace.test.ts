import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Test Case Marketplace heading is visible",
    "Verify marketplace shows test case cards or an empty state message",
  ],
  authPayload,
);
