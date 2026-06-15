import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { assertPageAny, assertPageLoaded } from "../helpers/prompts";

shortest(
  [
    "If Test Case Marketplace is not visible, expand Test Cases in the sidebar and click Marketplace.",
    assertPageLoaded("Test Case Marketplace"),
    assertPageAny("test case", "empty", "No test cases"),
  ],
  authPayload,
);
